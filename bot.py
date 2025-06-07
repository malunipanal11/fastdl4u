import os
import json
import asyncio
from pyrogram import Client, filters
from mega import Mega
from datetime import datetime

# Load from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = 123456  # Replace with your API ID
API_HASH = "your_api_hash"  # Replace with your API HASH
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split()]
MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")

bot = Client("storage_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
mega = Mega().login(MEGA_EMAIL, MEGA_PASSWORD)

upload_mode = {}

# Local serial tracking
file_count = {"img": 0, "vid": 0, "aud": 0}

def get_serial(file_type):
    file_count[file_type] += 1
    return f"{file_type}{file_count[file_type]}"

async def auto_delete_message(msg, delay=30):
    await asyncio.sleep(delay)
    await msg.delete()

async def auto_delete_file(msg, delay=600):
    await asyncio.sleep(delay)
    await msg.delete()

# Upload handler
@bot.on_message(filters.command("upload") & filters.user(ADMIN_IDS))
async def start_upload(client, message):
    upload_mode[message.from_user.id] = True
    msg = await message.reply("Upload mode ON. Send files.")
    await auto_delete_message(msg)

@bot.on_message(filters.command("done") & filters.user(ADMIN_IDS))
async def done_upload(client, message):
    upload_mode.pop(message.from_user.id, None)
    msg = await message.reply("Upload mode OFF.")
    await auto_delete_message(msg)

@bot.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_and_upload(client, message):
    if upload_mode.get(message.from_user.id):
        media_type = None
        if message.photo:
            media_type = "img"
        elif message.video:
            media_type = "vid"
        elif message.audio:
            media_type = "aud"
        elif message.document:
            mime = message.document.mime_type or ""
            if "image" in mime:
                media_type = "img"
            elif "video" in mime:
                media_type = "vid"
            elif "audio" in mime:
                media_type = "aud"

        if media_type:
            filename = get_serial(media_type)
            dl_path = await message.download(file_name=filename)
            mega.upload(dl_path, f"telegram_upload/{media_type.upper()}S/{filename}")
            os.remove(dl_path)

            msg = await message.reply(f"✅ Uploaded `{filename}` successfully.")
            await auto_delete_message(msg)
        else:
            msg = await message.reply("❌ Unsupported file type.")
            await auto_delete_message(msg)

# Show one random file from MEGA
@bot.on_message(filters.command(["images", "videos", "audio"]))
async def get_random_file(client, message):
    category = message.command[0].upper() + "S"
    folder = mega.find(f"telegram_upload/{category}")
    if folder:
        files = mega.get_files_in_node(folder)
        if files:
            import random
            selected = random.choice(list(files.values()))
            dl_link = mega.get_link(selected)
            msg = await message.reply(f"📁 Random {category[:-1]}: {dl_link}")
            await auto_delete_file(msg)
        else:
            await message.reply("❌ No files in this category.")
    else:
        await message.reply("❌ Category folder not found.")

@bot.on_message(filters.command("link") & filters.user(ADMIN_IDS))
async def link_file(client, message):
    args = message.text.split()
    if len(args) != 2:
        await message.reply("Usage: /link img1 or /link vid2")
        return

    serial = args[1]
    ftype = serial[:3]
    folder = mega.find(f"telegram_upload/{ftype.upper()}S")
    files = mega.get_files_in_node(folder)
    for file_id, file_data in files.items():
        if file_data['a']['n'] == serial:
            url = mega.get_link(file_data)
            await message.reply(f"🔗 Link for `{serial}`:\n{url}")
            return

    await message.reply("❌ File not found.")

@bot.on_message(filters.command("status"))
async def status(client, message):
    await message.reply("✅ Bot is online.")

@bot.on_message(filters.command("info"))
async def info(client, message):
    await message.reply("📦 Telegram → MEGA storage bot\nMade with ❤️")

bot.run()
