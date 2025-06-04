import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.constants import ChatAction
from typing import Dict, List

# Environment variables
TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-webhook-url/render")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI and Telegram application setup
app = FastAPI()
application: Application = Application.builder().token(TOKEN).build()

# User session states
user_states: Dict[int, bool] = {}
user_uploads: Dict[int, List[str]] = {}

# ----------------- Command Handlers -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = True
    user_uploads.setdefault(user_id, [])
    await update.message.reply_text(
        "✅ Upload mode ON. Send files or text.\nWhen done, send /done."
    )

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = False
    await update.message.reply_text("✅ Upload mode OFF.")

async def list_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uploads = user_uploads.get(user_id, [])
    images = [item for item in uploads if item.startswith("image:")]
    if not images:
        await update.message.reply_text("❌ No images uploaded yet.")
    else:
        await update.message.reply_text(
            "📸 Uploaded images:\n" + "\n".join(img.replace("image:", "") for img in images)
        )

# ----------------- File/Text Handler -----------------

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_states.get(user_id, False):
        return  # Ignore unless in upload mode

    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "image"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.text:
        file_id = update.message.text
        file_type = "text"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"

    if file_id and file_type:
        user_uploads[user_id].append(f"{file_type}:{file_id}")
        await update.message.reply_text(f"✅ Received {file_type}")

# ----------------- Setup -----------------

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("done", done))
application.add_handler(CommandHandler("images", list_images))

application.add_handler(MessageHandler(
    filters.PHOTO | filters.VIDEO | filters.Document.ALL |
    filters.AUDIO | filters.VOICE | filters.TEXT,
    handle_file
))

# ----------------- FastAPI -----------------

@app.on_event("startup")
async def startup_event():
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("add", "Enter upload mode"),
        BotCommand("done", "Exit upload mode"),
        BotCommand("images", "List uploaded images")
    ])
    logger.info("✅ Webhook and commands registered.")
    await application.start()

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot is running."}
