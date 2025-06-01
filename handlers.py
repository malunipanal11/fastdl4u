import aiohttp
from aiogram import Router, types, F
from aiogram.types import Message
from config import ADMIN_IDS, GOFILE_TOKEN
import json

router = Router()


@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("👋 Welcome! Send me a file and I’ll upload it to GoFile.")


@router.message(F.document)
async def upload_file(message: Message, bot):
    file = message.document
    file_id = file.file_id
    file_name = file.file_name

    # Get file from Telegram servers
    telegram_file = await bot.get_file(file_id)
    file_path = telegram_file.file_path
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

    # Get best GoFile server
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.gofile.io/getServer?token={GOFILE_TOKEN}") as resp:
                data = await resp.json()
                server = data["data"]["server"]
                upload_url = f"https://{server}.gofile.io/uploadFile"

                # Upload file
                async with session.get(file_url) as file_response:
                    file_data = await file_response.read()
                    form = aiohttp.FormData()
                    form.add_field("file", file_data, filename=file_name)
                    form.add_field("token", GOFILE_TOKEN)

                    async with session.post(upload_url, data=form) as upload_resp:
                        upload_data = await upload_resp.json()

                        if upload_data["status"] == "ok":
                            file_link = upload_data["data"]["downloadPage"]
                            await message.reply(f"✅ Uploaded: [Download File]({file_link})", disable_web_page_preview=True)
                        else:
                            await message.reply("❌ Upload failed.")
    except Exception as e:
        await message.reply(f"❌ Error uploading file:\n{str(e)}")
