import logging
from aiogram import Bot, Dispatcher, executor, types
from handlers import (
    handle_start,
    handle_add_file,
    handle_random_file,
    handle_get_code,
    handle_secret_list,
)
import os

API_TOKEN = os.getenv("BOT_TOKEN")  # Set this in your environment or .env

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Command: /start
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await handle_start(message)

# Admin Command: /addfile
@dp.message_handler(commands=["addfile"])
async def add_file_cmd(message: types.Message):
    await message.reply("Send a file with caption as 'image', 'video', or 'audio'.")

@dp.message_handler(commands=["addsecret"])
async def add_secret_cmd(message: types.Message):
    await message.reply("Send a file to store as secret. It will remain private.")

# Admin Command: /addlink
@dp.message_handler(commands=["addlink"])
async def add_link_cmd(message: types.Message):
    await message.reply("Send a platform link (Facebook, YouTube, etc.)")

# Command: /img
@dp.message_handler(commands=["img"])
async def get_image(message: types.Message):
    await handle_random_file(message, category="images")

# Command: /vid
@dp.message_handler(commands=["vid"])
async def get_video(message: types.Message):
    await handle_random_file(message, category="videos")

# Command: /aud
@dp.message_handler(commands=["aud"])
async def get_audio(message: types.Message):
    await handle_random_file(message, category="audios")

# Command: /get <code>
@dp.message_handler(lambda m: m.text.startswith("/get "))
async def get_by_code(message: types.Message):
    code = message.text.split(" ", 1)[1]
    await handle_get_code(message, code)

# Admin Command: /secret
@dp.message_handler(commands=["secret"])
async def secret_list(message: types.Message):
    await handle_secret_list(message)

# File upload with document
@dp.message_handler(content_types=["document"])
async def upload_file(message: types.Message):
    if message.caption:
        caption = message.caption.strip().lower()
        if caption in ["image", "video", "audio"]:
            await handle_add_file(message, category=caption)
        elif caption == "secret":
            await handle_add_file(message, category="secret")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
