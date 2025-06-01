import os
import uuid
import logging
from io import BytesIO
from collections import defaultdict

from fastapi import FastAPI, Request
from dotenv import load_dotenv
import requests

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
app = FastAPI()

uploaded_files = defaultdict(list)
user_categories = {}

# Attach router to dispatcher
dp.include_router(router)

# /start command
@router.message(F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Welcome! Use /add <category> and send me files.")

# /add command
@router.message(F.text.startswith("/add"))
async def cmd_add(message: types.Message):
    args = message.text.strip().split()
    if len(args) < 2:
        await message.reply("❗ Usage: /add <category>")
        return
    category = args[1]
    user_categories[message.from_user.id] = category
    await message.reply(f"📁 Now send files to add in category: {category}")

# File handler
@router.message()
async def handle_files(message: types.Message):
    user_id = message.from_user.id
    category = user_categories.get(user_id)

    if not category:
        await message.reply("❗ Use /add <category> before sending files.")
        return

    file_info = None
    filename = None
    file_bytes = BytesIO()

    if message.document:
        file_info = message.document
        filename = file_info.file_name
    elif message.photo:
        file_info = message.photo[-1]
        filename = f"photo_{file_info.file_id}.jpg"
    else:
        await message.reply("❗ Unsupported file type.")
        return

    try:
        tg_file = await bot.get_file(file_info.file_id)
        file = await bot.download_file(tg_file.file_path)
        file_bytes.write(file.read())
        file_bytes.seek(0)

        upload_result = upload_to_gofile_bytes(file_bytes, filename, category)
        if upload_result["success"]:
            await message.reply(f"✅ Uploaded: {upload_result['data']['url']}")
        else:
            await message.reply(f"❌ Upload failed: {upload_result['message']}")
    except Exception as e:
        logging.exception("File handling failed")
        await message.reply("❌ Error while processing the file.")

# Upload to GoFile
def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer", params={"token": GOFILE_TOKEN})
        server_resp.raise_for_status()
        server_data = server_resp.json()

        if server_data.get("status") != "ok":
            return {"success": False, "message": "Failed to get GoFile server."}

        server = server_data["data"]["server"]
        files = {"file": (filename, file_bytes)}
        data = {"token": GOFILE_TOKEN}
        res = requests.post(f"https://{server}.gofile.io/uploadFile", files=files, data=data)
        res.raise_for_status()
        result = res.json()

        if result["status"] == "ok":
            file_data = {
                "id": str(uuid.uuid4()),
                "name": filename,
                "url": result["data"]["downloadPage"],
                "code": result["data"]["code"]
            }
            uploaded_files[category].append(file_data)
            return {"success": True, "data": file_data}
        return {"success": False, "message": result.get("message", "Unknown error")}
    except Exception as e:
        logging.exception("Upload failed")
        return {"success": False, "message": str(e)}

# Webhook
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()
