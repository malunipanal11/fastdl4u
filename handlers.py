import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from config import ADMIN_IDS, EXPIRE_COMMANDS

router = Router()

@router.message(CommandStart())
async def handle_start(message: types.Message):
    await message.answer("👋 Hello! Send me a file, and I’ll upload it to GoFile.io and give you a download link.")

@router.message(Command("help"))
async def handle_help(message: types.Message):
    await message.answer("Just send a file or media to get a GoFile download link. Admins can use /admin.")

@router.message(Command("admin"))
async def handle_admin(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👮‍♂️ Admin access granted.")
    else:
        await message.answer("🚫 You are not an admin.")

@router.message(lambda m: m.document or m.photo or m.video or m.audio)
async def handle_media(message: types.Message):
    file = message.document or message.photo[-1] or message.video or message.audio
    file_id = file.file_id
    file_name = getattr(file, 'file_name', 'media')
    
    tg_file = await message.bot.get_file(file_id)
    file_path = tg_file.file_path
    downloaded = await message.bot.download_file(file_path)

    # Simulated GoFile.io upload
    url = f"https://gofile.io/d/fakefileid/{file_name}"
    await message.answer(f"✅ Uploaded! Download link: {url}")

    # Optional: auto-delete the original media message
    # await asyncio.sleep(EXPIRE_COMMANDS.get("media", 600))
    # await message.delete()
