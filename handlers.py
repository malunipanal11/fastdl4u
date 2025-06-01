# handlers.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ContentType
import asyncio
import functools
import logging

from config import ADMIN_IDS, EXPIRE_COMMANDS
from gofile import upload_to_gofile, get_random_file, get_file_by_code, get_all_files_by_type, delete_file

router = Router()
logging.basicConfig(level=logging.INFO)

# Dynamic keyboards
def get_admin_controls(file_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶ Play", callback_data=f"play_{file_id}"),
        InlineKeyboardButton(text="👁 Download", callback_data=f"download_{file_id}"),
        InlineKeyboardButton(text="❌ Delete", callback_data=f"delete_{file_id}")
    ]])

def get_user_controls(file_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶ View", callback_data=f"play_{file_id}")
    ]])

# /start command
@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    text = "👋 Welcome! Use the menu or send a command."
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🖼 Images", callback_data="img"),
        InlineKeyboardButton(text="🎞 Videos", callback_data="vid"),
        InlineKeyboardButton(text="🎷 Audio", callback_data="aud")
    ]])

    if is_admin:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="➕ Add File", callback_data="addfile"),
            InlineKeyboardButton(text="🔒 Add Secret", callback_data="addsecret"),
            InlineKeyboardButton(text="🔗 Add Link", callback_data="addlink")
        ])
    await message.answer(text, reply_markup=kb)

# File categories
@router.message(Command("img"))
async def handle_img(message: Message):
    await send_random_file(message, "images")

@router.message(Command("vid"))
async def handle_vid(message: Message):
    await send_random_file(message, "videos")

@router.message(Command("aud"))
async def handle_aud(message: Message):
    await send_random_file(message, "audios")

async def send_random_file(message: Message, category: str):
    file = get_random_file(category)
    if not file:
        await message.answer("No files found.")
        return

    kb = get_admin_controls(file["id"]) if message.from_user.id in ADMIN_IDS else get_user_controls(file["id"])
    sent = await message.answer(file["url"], reply_markup=kb)
    await asyncio.sleep(EXPIRE_COMMANDS.get(category[:-1], 600))
    try:
        await sent.delete()
    except:
        pass

# /get CODE
@router.message(F.text.startswith("/get "))
async def cmd_get_code(message: Message):
    code = message.text.split("/get ")[1].strip()
    file = get_file_by_code(code)
    if not file:
        await message.answer("Invalid code.")
        return

    kb = get_user_controls(file["id"])
    sent = await message.answer(file["url"], reply_markup=kb)
    await asyncio.sleep(EXPIRE_COMMANDS["code"])
    try:
        await sent.delete()
        await message.delete()
    except:
        pass

# Admin secret list
@router.message(Command("secret"))
async def list_secret(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("You are not authorized.")
        return

    files = get_all_files_by_type("secret")
    if not files:
        await message.answer("No secret files.")
        return

    for file in files:
        kb = get_admin_controls(file["id"])
        await message.answer(f"{file['url']} | Code: {file['code']}", reply_markup=kb)

upload_waiting = {}

# Handle button callbacks
@router.callback_query(F.data)
async def callbacks(call: CallbackQuery):
    data = call.data
    user_id = call.from_user.id

    if data in ["img", "vid", "aud"]:
        await call.answer()
        await send_random_file(call.message, {"img": "images", "vid": "videos", "aud": "audios"}[data])

    elif data.startswith("play_") or data.startswith("download_"):
        await call.answer("Feature coming soon!")

    elif data.startswith("delete_") and user_id in ADMIN_IDS:
        file_id = data.split("_", 1)[1]
        delete_file(file_id)
        await call.message.delete()

    elif data == "addfile" and user_id in ADMIN_IDS:
        upload_waiting[user_id] = "file"
        await call.message.answer("📄 Please send the file to upload.")

# Handle uploads
@router.message(F.content_type.in_({
    ContentType.PHOTO, ContentType.VIDEO,
    ContentType.AUDIO, ContentType.DOCUMENT
}))
async def handle_file_upload(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS or upload_waiting.get(user_id) != "file":
        return

    file = None
    if message.photo:
        file = await message.bot.get_file(message.photo[-1].file_id)
    elif message.video:
        file = await message.bot.get_file(message.video.file_id)
    elif message.audio:
        file = await message.bot.get_file(message.audio.file_id)
    elif message.document:
        file = await message.bot.get_file(message.document.file_id)

    if not file:
        await message.answer("❌ File not supported.")
        return

    file_path = file.file_path
    file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_path}"
    logging.info(f"Uploading file from URL: {file_url}")

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, functools.partial(upload_to_gofile, file_url))

    if response["success"]:
        await message.answer(f"✅ Uploaded to GoFile: {response['data']['downloadPage']}")
    else:
        await message.answer("❌ Upload failed.")

    upload_waiting.pop(user_id, None)

# Register function for main.py
def register_handlers(dp):
    dp.include_router(router)
