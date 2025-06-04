import os
import logging
import aiohttp
from uuid import uuid4
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

# === Environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not GOFILE_TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing environment variables.")

GOFILE_API = f"https://api.gofile.io/uploadFile?token={GOFILE_TOKEN}"
FILE_DB = {}

# === Logging ===
logging.basicConfig(level=logging.INFO)

# === FastAPI app ===
app = FastAPI()

# === Telegram app ===
telegram_app = Application.builder().token(BOT_TOKEN).build()

# === Upload file to GoFile.io ===
async def upload_to_gofile(file_path):
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=os.path.basename(file_path))
            async with session.post(GOFILE_API, data=data) as resp:
                res_json = await resp.json()
                return res_json['data']['downloadPage'] if res_json['status'] == 'ok' else None

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and working!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Upload a file after using /add.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type = None
    tg_file = None
    name = None

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
        content = update.message.text
        file_type = 'texts'
        name = f"text_{uuid4().hex[:8]}.txt"
        with open(name, 'w') as f:
            f.write(content)
        gofile_link = await upload_to_gofile(name)
        os.remove(name)
        if gofile_link:
            FILE_DB.setdefault(file_type, []).append((name, gofile_link))
            await update.message.reply_text(f"✅ Text saved: {gofile_link}")
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
        await update.message.reply_text(f"✅ File saved in /{file_type} as #{len(FILE_DB[file_type]):04d}")
    else:
        await update.message.reply_text("❌ Upload failed.")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type = update.message.text[1:]
    files = FILE_DB.get(file_type, [])
    if not files:
        await update.message.reply_text(f"❌ No {file_type} stored yet.")
    else:
        message = f"📂 {file_type.upper()} FILES:\n\n"
        for i, (name, link) in enumerate(files, 1):
            message += f"#{i:04d} - {name}: {link}\n"
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

# === Register handlers ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("add", add))
telegram_app.add_handler(CommandHandler("files", list_files))
telegram_app.add_handler(CommandHandler("images", list_files))
telegram_app.add_handler(CommandHandler("videos", list_files))
telegram_app.add_handler(CommandHandler("audios", list_files))
telegram_app.add_handler(CommandHandler("texts", list_files))
telegram_app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_file))

# === FastAPI startup ===
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    await set_bot_commands(telegram_app)
    await telegram_app.start()

# === Webhook endpoint ===
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
