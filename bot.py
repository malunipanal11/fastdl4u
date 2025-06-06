import os
import logging
import httpx
import asyncio
import tempfile
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_DOMAIN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
application: Application = Application.builder().token(TOKEN).build()

# --- Upload Helpers ---
async def upload_to_gofile(file_path: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            server_resp = await client.get("https://api.gofile.io/getServer")
            server_data = server_resp.json()
            server = server_data["data"]["server"]
            upload_url = f"https://{server}.gofile.io/uploadFile"
            with open(file_path, "rb") as f:
                files = {"file": f}
                params = {"token": GOFILE_TOKEN}
                upload_resp = await client.post(upload_url, files=files, params=params)
            upload_data = upload_resp.json()
            if upload_data["status"] == "ok":
                return upload_data["data"]["downloadPage"]
    except Exception as e:
        logger.error(f"Gofile upload failed: {e}")
    return None

async def upload_to_fileio(file_path: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(file_path, "rb") as f:
                files = {'file': f}
                resp = await client.post("https://file.io", files=files)
            data = resp.json()
            if data.get("success"):
                return data["link"]
    except Exception as e:
        logger.error(f"File.io upload failed: {e}")
    return None

# --- Video Downloader ---
async def download_video(url: str) -> str | None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            ydl_opts = {
                'outtmpl': tmp_file.name,
                'format': 'best',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return tmp_file.name
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return None

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send a video link (YouTube, Instagram, etc.) and I'll return a downloadable link.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    await update.message.reply_text("⏳ Downloading...")

    file_path = await download_video(url)
    if not file_path:
        await update.message.reply_text("❌ Failed to download video.")
        return

    await update.message.reply_text("⏫ Uploading...")

    download_link = await upload_to_gofile(file_path)
    if not download_link:
        download_link = await upload_to_fileio(file_path)

    os.remove(file_path)

    if download_link:
        keyboard = [[
            InlineKeyboardButton("▶️ Play", url=download_link),
            InlineKeyboardButton("⬇️ Download", url=download_link)
        ]]
        await update.message.reply_text("✅ Done!", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("❌ Upload failed to both GoFile and File.io.")

# --- Register Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- FastAPI Webhook Setup ---
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.bot.set_my_commands([BotCommand("start", "Start the bot")])
    logger.info("✅ Webhook registered.")

@app.post("/")
async def telegram_webhook(req: Request):
    update = Update.de_json(await req.json(), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def health_check():
    return {"message": "Bot is live"}
