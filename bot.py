import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
import httpx
from dotenv import load_dotenv
import uuid

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_DOMAIN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

if not TOKEN or not WEBHOOK_URL or not GOFILE_TOKEN:
    raise ValueError("Environment variables not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

app = FastAPI()
application: Application = Application.builder().token(TOKEN).build()

# Downloader function
async def download_video(url: str) -> tuple[bytes, str]:
    try:
        filename = f"/tmp/{uuid.uuid4()}.mp4"
        ydl_opts = {
            'format': 'best',
            'outtmpl': filename,
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'geo_bypass': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            }
        }

        # If you have cookie file (e.g., for Instagram)
        if os.path.exists("instagram_cookies.txt"):
            ydl_opts["cookiefile"] = "instagram_cookies.txt"

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open(filename, 'rb') as f:
            return f.read(), filename
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        raise

# Gofile uploader
async def upload_to_gofile(file_bytes: bytes, filename: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            server_resp = await client.get("https://api.gofile.io/getServer")
            server_data = server_resp.json()
            server = server_data["data"]["server"]

            files = {"file": (filename, file_bytes)}
            params = {"token": GOFILE_TOKEN}
            upload_url = f"https://{server}.gofile.io/uploadFile"

            upload_resp = await client.post(upload_url, files=files, params=params)
            upload_data = upload_resp.json()

            return upload_data["data"]["downloadPage"]
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise

# Telegram commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send a video link (YouTube, Instagram, TikTok, etc.), and I'll give you a download link."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("http"):
        return

    await update.message.reply_text("⏳ Downloading...")
    try:
        video_bytes, filename = await
