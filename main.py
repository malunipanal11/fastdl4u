import os import json import logging import requests from fastapi import FastAPI, Request from fastapi.responses import HTMLResponse from fastapi.templating import Jinja2Templates from fastapi.staticfiles import StaticFiles from telegram import Bot, Update from telegram.constants import ParseMode from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes from download_and_upload import download_video, upload_to_fileio

Logging

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

Config

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "YOUR_TELEGRAM_TOKEN" BASE_URL = os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:8000"

FastAPI app

app = FastAPI() templates = Jinja2Templates(directory="templates") app.mount("/static", StaticFiles(directory="static"), name="static")

Telegram Bot

bot = Bot(token=TELEGRAM_TOKEN) telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

@app.get("/", response_class=HTMLResponse) async def home(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.post("/webhook/{token}") async def webhook(token: str, request: Request): if token != TELEGRAM_TOKEN: return {"error": "Invalid token"} data = await request.json() update = Update.de_json(data, bot) await telegram_app.process_update(update) return {"status": "ok"}

@telegram_app.command("start") async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("👋 Send me a video or audio link to download.")

@telegram_app.message_handler(filters.TEXT & ~filters.COMMAND) async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE): link = update.message.text chat_id = update.effective_chat.id msg = await update.message.reply_text("🔄 Processing your request...")

try:
    video = download_video(link)
    file_link = upload_to_fileio(video['file_path'])

    caption = f"<b>{video['title']}</b>\n"
    caption += f"Duration: {video['duration']}s\n"
    caption += f"Size: {round(video['filesize'] / 1024 / 1024, 2)} MB\n"
    caption += f"Link: {video['webpage_url']}"

    await context.bot.send_video(chat_id=chat_id, video=open(video['file_path'], 'rb'),
                                 caption=caption, parse_mode=ParseMode.HTML)

    await msg.edit_text(f"✅ Done! Download via File.io: {file_link}")

except Exception as e:
    logger.error("Error processing video: %s", str(e))
    await msg.edit_text("❌ Failed to process the video. Try another link.")

@app.on_event("startup") async def startup(): webhook_url = f"{BASE_URL}/webhook/{TELEGRAM_TOKEN}" await telegram_app.bot.set_webhook(webhook_url) logger.info(f"✅ Webhook set to {webhook_url}") telegram_app.run_polling()  # Optional fallback

if name == 'main': import uvicorn uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

