import os
import uvicorn
import json
import uuid
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from yt_dlp import YoutubeDL
import requests

# === CONFIGURATION ===
BOT_TOKEN = "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw"
WEBHOOK_URL = f"https://fastdl4u.onrender.com/webhook/{BOT_TOKEN}"
DOWNLOAD_FOLDER = "downloads"
JSON_LOG = "file_log.json"
FILE_IO_API = "https://file.io"

# Ensure downloads folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# === FASTAPI SETUP ===
app = FastAPI()
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads")
templates = Jinja2Templates(directory="templates")

# === TELEGRAM SETUP ===
bot = Bot(token=BOT_TOKEN)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# === UTILITIES ===
def save_log(data):
    try:
        with open(JSON_LOG, "r") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = []

    log.append(data)
    with open(JSON_LOG, "w") as f:
        json.dump(log, f, indent=2)

def generate_filename(original):
    base, ext = os.path.splitext(original)
    filename = f"{base}{ext}"
    count = 1
    while os.path.exists(os.path.join(DOWNLOAD_FOLDER, filename)):
        filename = f"{base}_{count}{ext}"
        count += 1
    return filename

def upload_to_fileio(filepath):
    with open(filepath, "rb") as f:
        res = requests.post(FILE_IO_API, files={"file": f})
    return res.json().get("link")

# === TELEGRAM HANDLERS ===
async def start(update: Update, context):
    await update.message.reply_text("📥 Send me a media link and I will download it for you!")

async def handle_message(update: Update, context):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing your link...")

    try:
        with YoutubeDL({'outtmpl': f"{DOWNLOAD_FOLDER}/%(title).200B.%(ext)s"}) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        file_link = upload_to_fileio(filename)
        name = os.path.basename(filename)
        await update.message.reply_document(document=open(filename, "rb"), filename=name)
        await update.message.reply_text(f"📁 Web Download Link: {file_link}")
        
        save_log({
            "title": info.get("title"),
            "file": name,
            "url": file_link
        })

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === WEB ROUTES ===
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        with open(JSON_LOG, "r") as f:
            files = json.load(f)
    except:
        files = []
    return templates.TemplateResponse("index.html", {"request": request, "files": files})

@app.get("/play/{filename}", response_class=FileResponse)
async def play_file(filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4")
    return HTMLResponse("File not found", status_code=404)

@app.get("/delete/{filename}")
async def delete_file(filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return HTMLResponse("Deleted", status_code=200)

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return HTMLResponse("Invalid token", status_code=403)

    data = await request.json()
    update = Update.de_json(data, bot)
    await telegram_app.update_queue.put(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook set to", WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()

# === MAIN ENTRY ===
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))