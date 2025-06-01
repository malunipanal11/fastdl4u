import os
import uuid
import logging
from io import BytesIO
from collections import defaultdict

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

# Bot setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# In-memory storage
uploaded_files = defaultdict(list)
user_categories = {}

logging.basicConfig(level=logging.INFO)

# /start command
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("👋 Welcome! Use /add <category> and then send me files to upload.")

# /add <category> command
@dp.message(commands=["add"])
async def cmd_add(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Usage: /add <category>")
        return
    category = args[1]
    user_categories[message.from_user.id] = category
    await message.reply(f"📁 Category set to: {category}. Now send the files.")

# Upload handler
@dp.message()
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    category = user_categories.get(user_id)

    if not category:
        await message.reply("❗ Use /add <category> before sending files.")
        return

    file_info = None
    filename = None
    file_bytes = BytesIO()

    try:
        if message.document:
            file_info = message.document
            filename = file_info.file_name
        elif message.photo:
            file_info = message.photo[-1]  # highest quality photo
            filename = f"photo_{file_info.file_id}.jpg"
        else:
            await message.reply("❗ Unsupported file type.")
            return

        tg_file = await bot.get_file(file_info.file_id)
        file_path = tg_file.file_path
        file = await bot.download_file(file_path)
        file_bytes.write(file.read())
        file_bytes.seek(0)

        # Upload to GoFile
        upload_result = upload_to_gofile_bytes(file_bytes, filename, category)
        if upload_result["success"]:
            url = upload_result["data"]["url"]
            await message.reply(f"✅ Uploaded: {url}")
        else:
            await message.reply(f"❌ Failed to upload:\n{upload_result['message']}")
    except Exception as e:
        logging.exception("Error handling file")
        await message.reply("❌ Error occurred while processing the file.")

# GoFile upload function
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer", params={"token": GOFILE_TOKEN})
        server_resp.raise_for_status()
        server_data = server_resp.json()

        if server_data.get("status") != "ok":
            return {"success": False, "message": "Failed to get GoFile server."}

        server = server_data["data"]["server"]
        upload_url = f"https://{server}.gofile.io/uploadFile"
        files = {"file": (filename, file_bytes)}
        data = {"token": GOFILE_TOKEN}

        res = requests.post(upload_url, files=files, data=data)
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

# Webhook handler
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        update_data = await request.json()
        await dp.feed_raw_update(bot, update_data, update_type="webhook")
        return {"ok": True}
    except Exception as e:
        logging.exception("Webhook processing failed")
        return {"ok": False, "error": str(e)}

# Startup
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook set successfully.")

# Shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()
    logging.info("Bot shutdown complete.")
