from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.enums import ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
import uuid
import requests
import logging
from io import BytesIO

# Load .env variables
load_dotenv()

# Env vars
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

if not WEBHOOK_DOMAIN:
    raise ValueError("WEBHOOK_DOMAIN not set!")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = WEBHOOK_DOMAIN + WEBHOOK_PATH

# Initialize bot & dispatcher
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# FastAPI app
app = FastAPI()

# Track uploaded files
uploaded_files = {
    "images": [],
    "videos": [],
    "files": []
}

logging.basicConfig(level=logging.INFO)

# ✅ Upload function with GOFILE_TOKEN
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        gofile_token = os.getenv("GOFILE_TOKEN")
        server_resp = requests.get("https://api.gofile.io/getServer", params={"token": gofile_token})
        server_resp.raise_for_status()
        server_data = server_resp.json()

        if server_data.get("status") != "ok":
            return {"success": False, "message": "Failed to get GoFile server."}

        server = server_data["data"]["server"]

        file_bytes.seek(0)
        files = {"file": (filename, file_bytes)}
        upload_url = f"https://{server}.gofile.io/uploadFile"
        res = requests.post(upload_url, files=files, data={"token": gofile_token})
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

# === Bot handlers ===

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("👋 Welcome! Send me a file and I’ll upload it to GoFile.")

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
            await message.answer(f"❌ Failed to upload:\n{result['message']}")

# === FastAPI events and webhook ===

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    update_data = await request.body()
    await dp.feed_raw_update(bot, update_data, update_type="webhook")
    return {"ok": True}

@app.get("/")
async def health():
    return {"status": "ok"}
