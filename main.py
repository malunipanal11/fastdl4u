import os
import logging
from io import BytesIO
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import Update
import requests
import uuid

# Config
TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or "https://your.domain/webhook"

# Logging
logging.basicConfig(level=logging.INFO)

# FastAPI App
app = FastAPI()

# Telegram Bot Setup
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# In-memory storage
uploaded_files = {
    "images": [],
    "videos": [],
    "audios": [],
    "files": []
}


# File type categorization
def detect_type(filename: str) -> str:
    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "images"
    elif filename.lower().endswith((".mp4", ".mov", ".mkv")):
        return "videos"
    elif filename.lower().endswith((".mp3", ".wav", ".ogg")):
        return "audios"
    else:
        return "files"


# Upload to GoFile using BytesIO
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer")
        server = server_resp.json()["data"]["server"]

        files = {"file": (filename, file_bytes)}
        upload_url = f"https://{server}.gofile.io/uploadFile"
        res = requests.post(upload_url, files=files)

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
            return {"success": False, "message": result.get("message")}
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return {"success": False, "message": str(e)}


# Handler: /start command
@router.message(lambda msg: msg.text == "/start")
async def cmd_start(message: types.Message):
    kb = [
        [KeyboardButton(text="Images"), KeyboardButton(text="Videos")],
        [KeyboardButton(text="Audio"), KeyboardButton(text="Add File")],
        [KeyboardButton(text="Add Secret"), KeyboardButton(text="Add Link")]
    ]
    await message.answer(
        "👋 Welcome! Use the menu or send a command.",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )


# Handler: file upload
@router.message(lambda msg: msg.document or msg.photo or msg.video or msg.audio)
async def handle_upload(message: types.Message):
    filename = "file"
    file_id = None

    if message.document:
        file_id = message.document.file_id
        filename = message.document.file_name
    elif message.photo:
        file_id = message.photo[-1].file_id
        filename = "photo.jpg"
    elif message.video:
        file_id = message.video.file_id
        filename = "video.mp4"
    elif message.audio:
        file_id = message.audio.file_id
        filename = message.audio.file_name or "audio.mp3"
    else:
        await message.reply("❌ No valid file found.")
        return

    try:
        tg_file = await bot.get_file(file_id)
        file_path = tg_file.file_path
        file_content = await bot.download_file(file_path)
        file_bytes = BytesIO(file_content.read())

        category = detect_type(filename)
        result = upload_to_gofile_bytes(file_bytes, filename, category)

        if result["success"]:
            data = result["data"]
            await message.reply(
                f"✅ File uploaded!\n"
                f"🔗 <code>{data['url']}</code>\n"
                f"🆔 Code: <code>{data['code']}</code>"
            )
        else:
            await message.reply("❌ Failed to upload file.")
    except Exception as e:
        logging.error(f"Handler error: {e}")
        await message.reply("❌ Error processing file.")


# Webhook handler
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp._process_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"ok": False}


# Startup hook
@app.on_event("startup")
async def on_startup():
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL not set.")
        return
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")


# Shutdown hook
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("🛑 Webhook deleted.")
