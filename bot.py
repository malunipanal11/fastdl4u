import os
import logging
import random
import httpx
from typing import Dict, List

from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== CONFIG ==========
TOKEN = os.getenv("BOT_TOKEN")  # Set this in Render's environment
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# ========== SETUP ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

app = FastAPI()
application: Application = Application.builder().token(TOKEN).build()

user_upload_mode: Dict[int, bool] = {}
user_uploads: Dict[int, List[Dict[str, str]]] = {}

# ========== COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Not authorized.")
        return
    user_upload_mode[update.effective_user.id] = True
    await update.message.reply_text("✅ Upload mode ON. Send files or text.\nWhen done, send /done.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_upload_mode[update.effective_user.id] = False
    await update.message.reply_text("✅ Upload mode OFF.")

# ========== FILE.IO UPLOAD ==========
async def upload_to_fileio(file_bytes: bytes, filename: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, file_bytes)}
            response = await client.post("https://file.io", files=files)
            data = response.json()
            if data.get("success"):
                return data["link"]
            raise Exception(f"Upload failed: {data}")
    except Exception as e:
        logger.error(f"❌ File.io upload error: {e}")
        raise

# ========== FILE HANDLER ==========
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or not user_upload_mode.get(user_id, False):
        return

    tg_file, filename = None, "file"

    if update.message.document:
        tg_file = await update.message.document.get_file()
        filename = update.message.document.file_name
    elif update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        filename = "photo.jpg"
    elif update.message.video:
        tg_file = await update.message.video.get_file()
        filename = update.message.video.file_name or "video.mp4"
    elif update.message.audio:
        tg_file = await update.message.audio.get_file()
        filename = update.message.audio.file_name or "audio.mp3"
    elif update.message.text:
        try:
            link = await upload_to_fileio(update.message.text.encode(), "text.txt")
            user_uploads.setdefault(user_id, []).append({"type": "text", "url": link})
            await update.message.reply_text(f"✅ Uploaded: {link}")
            return
        except:
            await update.message.reply_text("❌ Upload failed.")
            return

    if tg_file:
        try:
            file_bytes = await tg_file.download_as_bytearray()
            link = await upload_to_fileio(file_bytes, filename)
            user_uploads.setdefault(user_id, []).append({"type": "file", "url": link})
            await update.message.reply_text(f"✅ Uploaded: {link}")
        except:
            await update.message.reply_text("❌ Upload failed.")

# ========== FASTAPI + TELEGRAM ==========

@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(f"{os.getenv('WEBHOOK_URL', '')}/")
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("add", "Enable upload mode"),
        BotCommand("done", "Disable upload mode")
    ])
    logger.info("✅ Webhook registered and bot is ready.")

@app.post("/")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Bot is alive."}

# ========== REGISTER HANDLERS ==========

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("done", done))
application.add_handler(MessageHandler(filters.ALL, handle_upload))
