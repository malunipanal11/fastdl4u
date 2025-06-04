import os
import logging
import aiohttp
from uuid import uuid4
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# Load environment variables
TOKEN = os.environ.get("BOT_TOKEN")
GOFILE_TOKEN = os.environ.get("GOFILE_TOKEN")
GOFILE_UPLOAD_API = "https://api.gofile.io/uploadFile"

logging.basicConfig(level=logging.INFO)
FILE_DB = {}

async def upload_to_gofile(file_path):
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=os.path.basename(file_path))
            data.add_field('token', GOFILE_TOKEN)  # Use your Gofile account token
            async with session.post(GOFILE_UPLOAD_API, data=data) as resp:
                res_json = await resp.json()
                if res_json['status'] == 'ok':
                    return res_json['data']['downloadPage']
                else:
                    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and working!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send the file now.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type, tg_file, name = None, None, None

    if update.message.document:
        tg_file = update.message.document
        file_type = 'documents'
    elif update.message.photo:
        tg_file = update.message.photo[-1]
        file_type = 'images'
    elif update.message.video:
        tg_file = update.message.video
        file_type = 'videos'
    elif update.message.audio:
        tg_file = update.message.audio
        file_type = 'audios'
    elif update.message.voice:
        tg_file = update.message.voice
        file_type = 'audios'
    elif update.message.text:
        file_type = 'texts'
        name = f"text_{uuid4().hex[:8]}.txt"
        with open(name, 'w') as f:
            f.write(update.message.text)
        gofile_link = await upload_to_gofile(name)
        os.remove(name)
        if gofile_link:
            FILE_DB.setdefault(file_type, []).append((name, gofile_link))
            await update.message.reply_text(f"✅ Text uploaded: {gofile_link}")
        else:
            await update.message.reply_text("❌ Failed to upload text.")
        return

    if not tg_file:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    file = await context.bot.get_file(tg_file.file_id)
    name = tg_file.file_name if hasattr(tg_file, 'file_name') else f"{file_type}_{uuid4().hex[:8]}"
    local_path = f"temp_{name}"
    await file.download_to_drive(local_path)

    gofile_link = await upload_to_gofile(local_path)
    os.remove(local_path)

    if gofile_link:
        FILE_DB.setdefault(file_type, []).append((name, gofile_link))
        await update.message.reply_text(f"✅ File saved under /{file_type} as #{len(FILE_DB[file_type]):04d}")
    else:
        await update.message.reply_text("❌ Upload failed.")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type = update.message.text[1:]  # /images -> 'images'
    files = FILE_DB.get(file_type, [])
    if not files:
        await update.message.reply_text(f"❌ No {file_type} stored yet.")
    else:
        message = f"📂 {file_type.upper()} FILES:\n\n"
        for i, (name, link) in enumerate(files, 1):
            message += f"#{i:04d} - {name}\n{link}\n\n"
        await update.message.reply_text(message, disable_web_page_preview=True)

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("add", "Add/upload a file"),
        BotCommand("files", "List all uploaded files"),
        BotCommand("images", "List uploaded images"),
        BotCommand("audios", "List uploaded audio files"),
        BotCommand("videos", "List uploaded videos"),
        BotCommand("texts", "List saved text messages"),
    ]
    await application.bot.set_my_commands(commands)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("files", list_files))
    app.add_handler(CommandHandler("images", list_files))
    app.add_handler(CommandHandler("videos", list_files))
    app.add_handler(CommandHandler("audios", list_files))
    app.add_handler(CommandHandler("texts", list_files))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_file))

    app.post_init = lambda _: set_bot_commands(app)

    print("==> Bot is running. Upload files after /add")
    app.run_polling()
