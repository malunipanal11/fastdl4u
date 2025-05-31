from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import asyncio
import os

from gofile import upload_to_gofile, get_random_file, get_file_by_code, get_all_files_by_type, delete_file
from config import ADMIN_IDS, EXPIRE_COMMANDS
from utils import generate_code, save_file_metadata

# --- Start Command ---
async def handle_start(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    commands = ["/img", "/vid", "/aud"]
    if is_admin:
        commands.extend(["/addfile", "/addsecret", "/addlink", "/link", "/secret"])

    for cmd in commands:
        kb.add(types.KeyboardButton(cmd))

    await message.answer("👋 Welcome to the bot!\nChoose an option below:", reply_markup=kb)

# --- Add File ---
async def handle_add_file(message: types.Message, category):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("❌ You are not authorized.")

    file = message.document or message.photo[-1] if message.photo else None
    if not file:
        return await message.reply("Please send a valid file (photo, document, etc.)")

    filename = file.file_name if hasattr(file, 'file_name') else f"{file.file_unique_id}.jpg"
    path = f"storage/{filename}"
    await file.download(destination_file=path)

    gofile_url, file_id = upload_to_gofile(path, category=category)
    save_file_metadata(file_id, gofile_url, category, message.from_user.id)

    await message.reply(f"✅ Uploaded: {gofile_url}")
    os.remove(path)

# --- Random File (img, vid, aud) ---
async def handle_random_file(message: types.Message, category):
    file = get_random_file(category)
    if not file:
        return await message.reply("⚠️ No files available.")

    delay = EXPIRE_COMMANDS.get(category[:-1], 600)
    sent = await message.reply(file["url"])

    await asyncio.sleep(delay)
    try:
        await sent.delete()
    except:
        pass

# --- Secret Code Access ---
async def handle_get_code(message: types.Message, code):
    file = get_file_by_code(code)
    if not file:
        return await message.reply("❌ Invalid code.")

    sent = await message.reply(f"🔐 Secret file: {file['url']}")
    await asyncio.sleep(EXPIRE_COMMANDS["code"])
    try:
        await sent.delete()
        await message.delete()
    except:
        pass

# --- List Secret Files ---
async def handle_secret_list(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("Unauthorized.")

    files = get_all_files_by_type("secret")
    if not files:
        return await message.reply("No secret files available.")

    for file in files:
        kb = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("▶ Play", url=file["url"]),
            InlineKeyboardButton("📥 Download", url=file["url"]),
            InlineKeyboardButton("❌ Delete", callback_data=f"delete_{file['id']}")
        )
        await message.answer(f"🔐 Code: {file['code']}", reply_markup=kb)
