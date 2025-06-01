import logging
import uuid
from io import BytesIO

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import asyncio
import os

# ENV & logging
TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, session=AiohttpSession())
dp = Dispatcher()
router = Router()
dp.include_router(router)
app = FastAPI()

# In-memory file store
uploaded_files = {
    "Images": [],
    "Documents": [],
    "Videos": [],
    "Audios": []
}

# Upload to GoFile
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer")
        server_resp.raise_for_status()
        server = server_resp.json()["data"]["server"]

        file_bytes.seek(0)  # Reset pointer before upload
        files = {"file": (filename, file_bytes)}

        upload_url = f"https://{server}.gofile.io/uploadFile"
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

# Upload handler
async def handle_upload(message: Message, file, category: str):
    try:
        file_info = await bot.get_file(file.file_id)
        file_path = file_info.file_path
        file_bytes = BytesIO()
        await bot.download_file(file_path, destination=file_bytes)

        filename = file.file_name if hasattr(file, "file_name") else f"{file.file_id}.bin"
        result = upload_to_gofile_bytes(file_bytes, filename, category)

        if result["success"]:
            url = result["data"]["url"]
            await message.reply(f"✅ File uploaded successfully:\n<a href='{url}'>{filename}</a>", parse_mode="HTML")
        else:
            await message.reply(f"❌ Failed to upload file:\n<code>{result['message']}</code>", parse_mode="HTML")

    except Exception as e:
        logging.exception("handle_upload error")
        await message.reply(f"❌ Error uploading file:\n<code>{str(e)}</code>", parse_mode="HTML")

# Command /start
@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("👋 Welcome! Use the menu or send a command.")

# Show file links
@router.message(F.text.in_(["Images", "Documents", "Videos", "Audios"]))
async def show_category(message: Message):
    category = message.text
    files = uploaded_files.get(category, [])
    if not files:
        await message.answer(f"No {category.lower()} uploaded yet.")
        return
    msg = f"📂 <b>{category}</b> files:\n\n"
    for f in files:
        msg += f"• <a href='{f['url']}'>{f['name']}</a>\n"
    await message.answer(msg, parse_mode="HTML")

# Handle files: photos, documents, videos, audios
@router.message(F.photo)
async def photo_handler(message: Message):
    await handle_upload(message, message.photo[-1], "Images")

@router.message(F.document)
async def document_handler(message: Message):
    await handle_upload(message, message.document, "Documents")

@router.message(F.video)
async def video_handler(message: Message):
    await handle_upload(message, message.video, "Videos")

@router.message(F.audio)
async def audio_handler(message: Message):
    await handle_upload(message, message.audio, "Audios")

# FastAPI root
@app.get("/", response_class=HTMLResponse)
def index():
    return "<h1>🚀 Telegram Bot with GoFile Uploader is running!</h1>"

# Start polling
@app.on_event("startup")
async def on_startup():
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling(bot))
