import os
import json
import requests
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# === Env Variables ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "https://yourdomain.com")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
LOG_FILE = "file_log.json"

# === FastAPI App ===
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Telegram App ===
telegram_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

# === Helper Functions ===
def save_to_log(data):
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        logs.append(data)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print("Log error:", e)

def fake_download(link, format):
    return {
        "title": "Sample Video",
        "thumbnail": "https://via.placeholder.com/400x200.png?text=Thumbnail",
        "duration": "123",
        "size": "5.4 MB",
        "quality": "720p",
        "file_url": "https://file.io/example",
        "file_name": "video.mp4"
    }

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    await update.message.reply_text("⏳ Processing your link...")

    result = fake_download(link, "video")
    try:
        file_data = requests.get(result["file_url"])
        with open(result["file_name"], "wb") as f:
            f.write(file_data.content)

        with open(result["file_name"], "rb") as f:
            await update.message.reply_video(
                video=f,
                caption=f"🎬 {result['title']} ({result['quality']}, {result['size']})"
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

    save_to_log(result)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

# === FastAPI Routes ===
@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h1>🚀 Social Downloader API is live</h1>"

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return JSONResponse(content={"ok": True})

@app.post("/api/process")
async def api_process(request: Request):
    data = await request.json()
    link = data.get("link")
    format = data.get("format", "video")

    result = fake_download(link, format)
    save_to_log(result)
    return result

# === Main Entrypoint ===
async def on_startup():
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await telegram_app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

@app.on_event("startup")
async def startup_event():
    await telegram_app.initialize()
    await telegram_app.start()
    await on_startup()
