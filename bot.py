from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest
import asyncio
import os
import random

from config import ADMIN_IDS, EXPIRE_COMMANDS
from gofile import upload_to_gofile, list_files, delete_file, get_random_file
from handlers import save_file_metadata, get_file_by_code, get_all_files_by_type

router = Router()

def admin_controls(file_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ Play", callback_data=f"play_{file_id}"),
         InlineKeyboardButton(text="📥 Download", callback_data=f"download_{file_id}"),
         InlineKeyboardButton(text="❌ Delete", callback_data=f"delete_{file_id}")]
    ])
    return kb

def user_controls(file_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ View", callback_data=f"play_{file_id}")]
    ])
    return kb

@router.message(CommandStart())
async def start_handler(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    commands = ["/addfile", "/addsecret", "/addlink", "/link", "/secret", "/img", "/vid", "/aud"] if is_admin else ["/img", "/vid", "/aud"]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(*[types.KeyboardButton(c) for c in commands])
    await message.answer("👋 Welcome! Choose a command below:", reply_markup=kb)

@router.message(Command("addfile"))
async def addfile_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ Unauthorized.")
    await message.answer("📤 Send up to 100 media files to upload and categorize.")

@router.message(Command("addsecret"))
async def addsecret_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ Unauthorized.")
    await message.answer("🔒 Send secret files for permanent access.")

@router.message(F.content_type.in_({"photo", "video", "audio"}))
async def handle_media(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        file = message.photo[-1] if message.photo else message.video or message.audio
        if file:
            category = "images" if message.photo else "videos" if message.video else "audios"
            path = await file.download()
            gofile_url, file_id = upload_to_gofile(path.name, category)
            save_file_metadata(file_id, gofile_url, category, message.from_user.id)
            await message.answer(f"✅ Uploaded: {gofile_url}")
            os.remove(path.name)

@router.message(Command(["img", "vid", "aud"]))
async def send_random_handler(message: types.Message):
    category = message.text[1:] + "s"
    file = get_random_file(category)
    if not file:
        return await message.answer("⚠️ No files found.")
    kb = admin_controls(file["id"]) if message.from_user.id in ADMIN_IDS else user_controls(file["id"])
    sent = await message.answer(file["url"], reply_markup=kb)
    delay = EXPIRE_COMMANDS.get(message.text[1:], 600)
    await asyncio.sleep(delay)
    try:
        await sent.delete()
    except TelegramBadRequest:
        pass

@router.message(F.text.startswith("/get "))
async def get_by_code_handler(message: types.Message):
    code = message.text.split("/get ")[1].strip()
    file = get_file_by_code(code)
    if not file:
        return await message.answer("❌ Invalid code.")
    kb = user_controls(file["id"])
    sent = await message.answer(file["url"], reply_markup=kb)
    await asyncio.sleep(EXPIRE_COMMANDS["code"])
    try:
        await sent.delete()
        await message.delete()
    except TelegramBadRequest:
        pass

@router.message(Command("secret"))
async def list_secret_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ Unauthorized.")
    files = get_all_files_by_type("secret")
    if not files:
        return await message.answer("ℹ️ No secret files.")
    for file in files:
        kb = admin_controls(file["id"])
        await message.answer(f"{file['url']} | Code: {file['code']}", reply_markup=kb)

@router.message(Command("addlink"))
async def add_link_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ Unauthorized.")
    await message.answer("🔗 Send a link (YouTube, Facebook, etc.) to auto-categorize.")

@router.message(Command("link"))
async def list_links_handler(message: types.Message):
    await message.answer("📦 List of links - [Feature In Progress]")

@router.callback_query(F.data.contains("_"))
async def callback_handler(callback: types.CallbackQuery):
    action, file_id = callback.data.split("_", 1)
    if action == "delete" and callback.from_user.id in ADMIN_IDS:
        delete_file(file_id)
        await callback.message.delete()
    elif action == "play":
        await callback.message.answer(callback.message.text)
    elif action == "download" and callback.from_user.id in ADMIN_IDS:
        await callback.message.answer("⬇️ Downloading file...")

def register_handlers(dp):
    dp.include_router(router)
