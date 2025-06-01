import logging
import uuid
from io import BytesIO
from collections import defaultdict
from aiogram import Router, F
from aiogram.types import Message, Document, PhotoSize
from aiogram.filters.command import Command
import requests
import os

router = Router()
user_categories = {}
uploaded_files = defaultdict(list)
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Welcome! Use /add <category> and send me files.")

@router.message(Command("add"))
async def cmd_add(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❗ Usage: /add <category>")
        return
    category = args[1]
    user_categories[message.from_user.id] = category
    await message.reply(f"📁 Now send files to add in category: {category}")

@router.message(F.document | F.photo)
async def handle_files(message: Message):
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
            file_info = message.photo[-1]  # highest resolution
            filename = f"photo_{file_info.file_id}.jpg"
        else:
            await message.reply("❗ Unsupported file type.")
            return

        file = await message.bot.download_file_by_id(file_info.file_id)
        file_bytes.write(file.read())

        result = upload_to_gofile_bytes(file_bytes, filename, category)
        if result["success"]:
            url = result["data"]["url"]
            await message.reply(f"✅ Uploaded: {url}")
        else:
            await message.reply(f"❌ Upload failed: {result['message']}")
    except Exception as e:
        logging.exception("Error handling file")
        await message.reply("❌ An error occurred.")

def upload_to_gofile_bytes(file_bytes: BytesIO, filename: str, category: str):
    try:
        server_resp = requests.get("https://api.gofile.io/getServer", params={"token": GOFILE_TOKEN})
        server_resp.raise_for_status()
        server_data = server_resp.json()

        if server_data.get("status") != "ok":
            return {"success": False, "message": "Failed to get GoFile server."}

        server = server_data["data"]["server"]
        file_bytes.seek(0)
        files = {"file": (filename, file_bytes)}
        upload_url = f"https://{server}.gofile.io/uploadFile"
        res = requests.post(upload_url, files=files, data={"token": GOFILE_TOKEN})
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
