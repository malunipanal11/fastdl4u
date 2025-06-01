import logging
import requests
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ContentType
from config import GOFILE_TOKEN

router = Router()

@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("👋 Hello! Send me a file and I’ll upload it to Gofile.")

@router.message(F.content_type.in_({ContentType.DOCUMENT, ContentType.VIDEO, ContentType.AUDIO, ContentType.PHOTO}))
async def upload_file(message: Message):
    file = await message.bot.get_file(message.document.file_id)
    file_path = file.file_path
    file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_path}"
    
    try:
        # Get Gofile server
        server_resp = requests.get(f"https://api.gofile.io/getServer?token={GOFILE_TOKEN}").json()
        server = server_resp["data"]["server"]
        upload_url = f"https://{server}.gofile.io/uploadFile"

        # Upload to Gofile
        file_bytes = await message.document.download(destination=bytes)
        response = requests.post(upload_url, files={"file": file_bytes}, data={"token": GOFILE_TOKEN})
        response.raise_for_status()

        link = response.json()["data"]["downloadPage"]
        await message.answer(f"✅ File uploaded:\n{link}")
    except Exception as e:
        logging.exception("Upload failed")
        await message.answer("❌ Upload failed: " + str(e))
