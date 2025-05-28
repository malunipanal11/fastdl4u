import os import uuid import json import aiofiles import requests import yt_dlp from fastapi import FastAPI, Request, Form from fastapi.responses import HTMLResponse, FileResponse from fastapi.templating import Jinja2Templates from fastapi.staticfiles import StaticFiles from telegram import Bot, Update from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

Telegram Bot Token

BOT_TOKEN = "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw"

Directories

DOWNLOAD_FOLDER = "downloads" os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

File Log

FILE_LOG = "file_log.json" if not os.path.exists(FILE_LOG): with open(FILE_LOG, 'w') as f: json.dump({}, f)

FastAPI App

app = FastAPI() app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads") templates = Jinja2Templates(directory="templates")

Telegram Bot App

telegram_app = Application.builder().token(BOT_TOKEN).build() bot = Bot(BOT_TOKEN)

Utility: Save log

def save_log(data): with open(FILE_LOG, 'w') as f: json.dump(data, f, indent=2)

Utility: Download media

def download_media(url): unique_id = str(uuid.uuid4()) ydl_opts = { 'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s.%(ext)s'), 'format': 'bestvideo+bestaudio/best', } with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=True) filename = ydl.prepare_filename(info) return filename, info

FastAPI Web Routes

@app.get("/", response_class=HTMLResponse) async def home(request: Request): files = os.listdir(DOWNLOAD_FOLDER) return templates.TemplateResponse("index.html", {"request": request, "files": files})

@app.post("/download") async def download(request: Request, url: str = Form(...)): try: filepath, info = download_media(url) filename = os.path.basename(filepath) with open(FILE_LOG) as f: log = json.load(f) log[filename] = info.get('title', filename) save_log(log) return templates.TemplateResponse("index.html", {"request": request, "files": os.listdir(DOWNLOAD_FOLDER), "message": f"Downloaded: {filename}"}) except Exception as e: return templates.TemplateResponse("index.html", {"request": request, "files": os.listdir(DOWNLOAD_FOLDER), "message": f"Error: {str(e)}"})

@app.get("/file/{filename}") async def serve_file(filename: str): file_path = os.path.join(DOWNLOAD_FOLDER, filename) if os.path.exists(file_path): return FileResponse(file_path) return {"error": "File not found"}

Telegram Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("👋 Send me a video URL to download.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE): url = update.message.text try: filepath, info = download_media(url) await update.message.reply_video(video=open(filepath, 'rb'), caption=f"🎬 {info.get('title', 'Downloaded')}\n📥 File ready.") except Exception as e: await update.message.reply_text(f"❌ Error: {str(e)}")

telegram_app.add_handler(CommandHandler("start", start)) telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup") async def startup(): print("✅ Starting bot...") await telegram_app.initialize() await telegram_app.start() await bot.set_webhook(f"https://fastdl4u.onrender.com/webhook/{BOT_TOKEN}")

@app.on_event("shutdown") async def shutdown(): print("🛑 Shutting down bot...") await telegram_app.stop()

@app.post("/webhook/{token}") async def webhook(request: Request, token: str): if token != BOT_TOKEN: return {"status": "unauthorized"} update_data = await request.json() update = Update.de_json(update_data, bot) await telegram_app.process_update(update) return {"status": "ok"}

