from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv
import os
import uuid
import requests
import logging
from io import BytesIO

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_DOMAIN") + WEBHOOK_PATH

# Initialize bot and dispatcher
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

app = FastAPI()

# In-memory storage
uploaded_files = {
    "images": [],
    "videos": [],
    "files": []
}

logging.basicConfig(level=logging.INFO)

# Upload to GoFile
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/servers")
        server_resp.raise_for_status()
        server = server_resp.json()["data"]["server"]

        file_bytes.seek(0)
        files = {"file": (filename, file_bytes)}

        upload_url = f"https://{server}.gofile.io/upload"
        res = requests.post(upload_url, files=files)
        res.raise_for_status()

        result = res.json()
        if result.get("status") == "ok":
            file_data = {
                "id": str(uuid.uuid4()),
                "name": filename,
                "url": result["data"]["downloadPage"],
                "code": result["data"]["code"]
            }
            uploaded_files[category].append(file_data)
            return {"success": True, "data": file_data}
        else:
            return {"success": False, "message": result.get("message", "Unknown error")}
    except Exception as e:
        logging.exception("Upload failed")
        return {"success": False, "message": str(e)}

# === Handlers ===

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("👋 Welcome! Use the menu or send a command.")

@router.message(F.text == "Images")
async def list_images(message: Message):
    images = uploaded_files.get("images", [])
    if not images:
        await message.answer("No images uploaded yet.")
    else:
        response = "\n".join(f"{file['name']}: {file['url']}" for file in images)
        await message.answer(response)

@router.message(F.text == "Videos")
async def list_videos(message: Message):
    videos = uploaded_files.get("videos", [])
    if not videos:
        await message.answer("No videos uploaded yet.")
    else:
        response = "\n".join(f"{file['name']}: {file['url']}" for file in videos)
        await message.answer(response)

@router.message(F.text == "Add File")
async def list_files(message: Message):
    files = uploaded_files.get("files", [])
    if not files:
        await message.answer("No files uploaded yet.")
    else:
        response = "\n".join(f"{file['name']}: {file['url']}" for file in files)
        await message.answer(response)

@router.message(F.document | F.photo | F.video | F.audio)
async def handle_upload(message: Message):
    file_type = None
    file = None
    filename = ""

    if message.photo:
        file_type = "images"
        file = message.photo[-1]
        filename = f"photo_{file.file_id}.jpg"
    elif message.video:
        file_type = "videos"
        file = message.video
        filename = f"video_{file.file_id}.mp4"
    elif message.document:
        file_type = "files"
        file = message.document
        filename = file.file_name or f"file_{file.file_id}"
    elif message.audio:
        file_type = "files"
        file = message.audio
        filename = file.file_name or f"audio_{file.file_id}.mp3"

    if file_type and file:
        file_obj = await bot.download(file)
        result = upload_to_gofile_bytes(file_obj, filename, file_type)

        if result["success"]:
            await message.answer(f"✅ Uploaded: {filename}\n🔗 {result['data']['url']}")
        else:
            await message.answer(f"❌ Failed to upload file:\n{result['message']}")

# === FastAPI events ===

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"message": "Internal server error"})

# === AIOHTTP webhook integration ===

app_router = web.RouteTableDef()

@app_router.post(WEBHOOK_PATH)
async def telegram_webhook(request: web.Request):
    return await SimpleRequestHandler(dispatcher=dp, bot=bot).handle(request)

setup_application(app, dp, bot=bot)
app.router.add_routes(app_router)
