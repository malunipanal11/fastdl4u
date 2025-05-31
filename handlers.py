from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from gofile import upload_to_gofile, get_random_file, get_file_by_code, get_all_files_by_type, delete_file
import asyncio

ADMIN_IDS = [123456789]  # Replace with real admin Telegram user IDs

async def handle_start(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🖼 Images", callback_data="img"),
        InlineKeyboardButton("🎞 Videos", callback_data="vid"),
        InlineKeyboardButton("🎧 Audio", callback_data="aud")
    )
    if is_admin:
        kb.add(
            InlineKeyboardButton("➕ Add File", callback_data="addfile"),
            InlineKeyboardButton("🔒 Add Secret", callback_data="addsecret"),
            InlineKeyboardButton("🔗 Add Link", callback_data="addlink")
        )
    await message.answer("Welcome to the bot!\nAvailable commands:", reply_markup=kb)

async def handle_add_file(message: types.Message, category):
    if not message.from_user.id in ADMIN_IDS:
        return
    if not message.document:
        await message.reply("Send a file to upload.")
        return

    file = message.document
    file_path = f"storage/{file.file_name}"
    await file.download(destination_file=file_path)

    url, file_id = upload_to_gofile(file_path, category=category)
    await message.reply(f"Uploaded successfully: {url}")

async def handle_random_file(callback_query: types.CallbackQuery, category):
    file = get_random_file(category)
    if file:
        await callback_query.message.answer(file['url'])
        delete_delay = 300 if category == "images" else 600
        await asyncio.sleep(delete_delay)
        await callback_query.message.delete()
    else:
        await callback_query.message.answer("No files available.")

async def handle_get_code(message: types.Message, code):
    file = get_file_by_code(code)
    if file:
        await message.answer(f"Secret file: {file['url']}")
        await asyncio.sleep(48 * 3600)  # 48 hrs
        await message.delete()
    else:
        await message.answer("Invalid code.")

async def handle_secret_list(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("You are not allowed.")
        return
    files = [f for f in get_all_files_by_type("secret")]
    if not files:
        await message.reply("No secret files.")
        return
    for f in files:
        kb = InlineKeyboardMarkup(row_width=3)
        kb.add(
            InlineKeyboardButton("▶ Play", url=f["url"]),
            InlineKeyboardButton("⏬ Download", url=f["url"]),
            InlineKeyboardButton("❌ Delete", callback_data=f"delete_{f['id']}")
        )
        await message.answer(f"Secret: {f['code']}", reply_markup=kb)
