from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import asyncio

from config import BOT_TOKEN, ADMIN_IDS, EXPIRE_COMMANDS
from gofile import upload_to_gofile, get_random_file, get_file_by_code, get_all_files_by_type, delete_file

# --- Button layouts ---
def get_admin_controls(file_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ Play", callback_data=f"play_{file_id}"),
         InlineKeyboardButton(text="📥 Download", callback_data=f"download_{file_id}"),
         InlineKeyboardButton(text="❌ Delete", callback_data=f"delete_{file_id}")]
    ])

def get_user_controls(file_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ View", callback_data=f"play_{file_id}")]
    ])

# --- Register all handlers ---
def register_handlers(dp):
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        is_admin = message.from_user.id in ADMIN_IDS
        text = "👋 Welcome! Use the menu or send a command."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Images", callback_data="img"),
             InlineKeyboardButton(text="🎞 Videos", callback_data="vid"),
             InlineKeyboardButton(text="🎧 Audio", callback_data="aud")]
        ])
        if is_admin:
            kb.inline_keyboard.append([
                InlineKeyboardButton(text="➕ Add File", callback_data="addfile"),
                InlineKeyboardButton(text="🔒 Add Secret", callback_data="addsecret"),
                InlineKeyboardButton(text="🔗 Add Link", callback_data="addlink"),
            ])
        await message.answer(text, reply_markup=kb)

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

    @router.callback_query(F.data)
    async def callbacks(call: CallbackQuery):
        data = call.data

        if "_" in data:
            action, file_id = data.split("_", 1)
            if action == "delete" and call.from_user.id in ADMIN_IDS:
                delete_file(file_id)
                await call.message.delete()
            elif action == "play":
                await call.message.answer(call.message.text)
            elif action == "download":
                await call.message.answer("🔽 Downloading...")
        else:
            if data == "img":
                await send_random_file(call.message, "images")
            elif data == "vid":
                await send_random_file(call.message, "videos")
            elif data == "aud":
                await send_random_file(call.message, "audios")
            elif data == "addfile":
                await call.message.answer("📤 Please send a file to upload.")
            elif data == "addsecret":
                await call.message.answer("🔐 Send your secret content.")
            elif data == "addlink":
                await call.message.answer("🔗 Send the link to store.")

    dp.include_router(router)
