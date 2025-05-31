from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import MessageToDeleteNotFound
import asyncio
import random
import os

from config import BOT_TOKEN, ADMIN_IDS, EXPIRE_COMMANDS
from gofile import upload_to_gofile, list_files, delete_file, get_random_file
from handlers import save_file_metadata, get_file_by_code, get_all_files_by_type, generate_code

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Inline Buttons ---
def admin_controls(file_id):
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("▶ Play", callback_data=f"play_{file_id}"),
        InlineKeyboardButton("📥 Download", callback_data=f"download_{file_id}"),
        InlineKeyboardButton("❌ Delete", callback_data=f"delete_{file_id}")
    )
    return kb

def user_controls(file_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("▶ View", callback_data=f"play_{file_id}"))
    return kb

# --- /start ---
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    is_admin = msg.from_user.id in ADMIN_IDS
    welcome = "👋 Welcome! Please choose a command below:"
    if is_admin:
        commands = ["/addfile", "/addsecret", "/addlink", "/link", "/secret", "/img", "/vid", "/aud"]
    else:
        commands = ["/img", "/vid", "/aud"]
    buttons = [types.KeyboardButton(c) for c in commands]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons)
    await msg.reply(welcome, reply_markup=kb)

# --- Add file (admin only) ---
@dp.message_handler(commands=["addfile"])
async def addfile_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.reply("Unauthorized.")
    await msg.reply("Send up to 100 media files to categorize and upload.")

# --- Secret add (permanent) ---
@dp.message_handler(commands=["addsecret"])
async def addsecret_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.reply("Unauthorized.")
    await msg.reply("Send secret files. Permanent access via secret code.")

# --- Auto-handle media ---
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def handle_media(msg: types.Message):
    if msg.from_user.id in ADMIN_IDS:
        file = msg.photo[-1] if msg.photo else msg.video or msg.audio
        if file:
            category = "images" if msg.photo else "videos" if msg.video else "audios"
            path = await file.download()
            gofile_url, file_id = upload_to_gofile(path.name, category)
            save_file_metadata(file_id, gofile_url, category, msg.from_user.id)
            await msg.reply(f"Uploaded: {gofile_url}")
            os.remove(path.name)

# --- /img /vid /aud ---
@dp.message_handler(commands=["img", "vid", "aud"])
async def send_random(msg: types.Message):
    category = msg.text[1:] + "s"  # img -> images
    file = get_random_file(category)
    if not file:
        return await msg.reply("No files found.")
    kb = admin_controls(file["id"]) if msg.from_user.id in ADMIN_IDS else user_controls(file["id"])
    caption = f"🎞 {category[:-1].capitalize()} Shared"
    sent = await msg.reply(file["url"], reply_markup=kb)
    delay = EXPIRE_COMMANDS.get(msg.text[1:], 600)
    await asyncio.sleep(delay)
    try:
        await sent.delete()
    except MessageToDeleteNotFound:
        pass

# --- /get <code> ---
@dp.message_handler(lambda m: m.text.startswith("/get "))
async def get_by_code(msg: types.Message):
    code = msg.text.split("/get ")[1].strip()
    file = get_file_by_code(code)
    if not file:
        return await msg.reply("Invalid code.")
    kb = user_controls(file["id"])
    sent = await msg.reply(file["url"], reply_markup=kb)
    await asyncio.sleep(EXPIRE_COMMANDS["code"])
    try:
        await sent.delete()
        await msg.delete()
    except:
        pass

# --- Secret list for admin ---
@dp.message_handler(commands=["secret"])
async def list_secret(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.reply("Unauthorized.")
    files = get_all_files_by_type("secret")
    if not files:
        return await msg.reply("No secret files.")
    for file in files:
        kb = admin_controls(file["id"])
        await msg.reply(f"{file['url']} | Code: {file['code']}", reply_markup=kb)

# --- Gofile link add/view ---
@dp.message_handler(commands=["addlink"])
async def add_link_cmd(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.reply("Unauthorized.")
    await msg.reply("Send any supported platform link (YouTube, Twitter, etc.).")

@dp.message_handler(commands=["link"])
async def list_links(msg: types.Message):
    # Show categorized links
    pass  # You can implement this similarly to `list_secret`

# --- Callback actions ---
@dp.callback_query_handler(lambda c: c.data)
async def callback_handler(call: types.CallbackQuery):
    action, file_id = call.data.split("_", 1)
    if action == "delete" and call.from_user.id in ADMIN_IDS:
        delete_file(file_id)
        await call.message.delete()
    elif action == "play":
        await call.message.reply(call.message.text)
    elif action == "download" and call.from_user.id in ADMIN_IDS:
        await call.message.reply("🔽 Downloading file...")

# --- Run ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
