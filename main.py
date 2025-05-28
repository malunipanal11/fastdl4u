import os
import json
import uuid
import shutil
import asyncio
import yt_dlp
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters

BOT_TOKEN = "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw"
BASE_URL = "https://file.io"
WEBHOOK_URL = f"https://fastdl4u.onrender.com/webhook/{BOT_TOKEN}"
DOWNLOAD_FOLDER = "downloads"
TEMPLATES_FOLDER = "templates"

app = FastAPI()
bot = Bot(token=BOT_TOKEN)
telegram_app = Application.builder().token(BOT_TOKEN).build()

templates = Jinja2Templates(directory=TEMPLATES_FOLDER)
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads")

file_log_path = "file_log.json"
if not os.path.exists(file_log_path):
    with open(file_log_path, "w") as f:
        json.dump({}, f)

def get_unique_filename(folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(folder, new_filename)):
        new_filename = f"{base}{counter}{ext}"
        counter += 1
    return new_filename

async def download_media(url):
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = ydl.prepare_filename(info)
    if not os.path.exists(title):
        return None, None
    original_name = os.path.basename(title)
    unique_name = get_unique_filename(DOWNLOAD_FOLDER, original_name)
    final_path = os.path.join(DOWNLOAD_FOLDER, unique_name)
    shutil.move(title, final_path)
    return final_path, unique_name

def upload_to_fileio(filepath):
    with open(filepath, "rb") as f:
        response = requests.post(BASE_URL, files={"file": f})
    return response.json().get("link")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    files = os.listdir(DOWNLOAD_FOLDER)
    with open(file_log_path, "r") as f:
        logs = json.load(f)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "files": files,
        "logs": logs
    })

@app.get("/play/{filename}", response_class=HTMLResponse)
async def play_file(request: Request, filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return templates.TemplateResponse("play.html", {
            "request": request,
            "file": f"/downloads/{filename}"
        })
    return HTMLResponse("File not found", status_code=404)

@app.get("/delete/{filename}")
async def delete_file(filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted"}
    return {"status": "not found"}

@telegram_app.message_handler(filters.COMMAND, command="start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a social media video link!")

@telegram_app.message_handler(filters.TEXT & ~filters.COMMAND)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    msg = await update.message.reply_text("Downloading...")
    path, filename = await download_media(url)
    if path:
        await bot.send_document(chat_id=update.effective_chat.id, document=open(path, "rb"))
        with open(file_log_path, "r") as f:
            logs = json.load(f)
        logs[filename] = url
        with open(file_log_path, "w") as f:
            json.dump(logs, f)
        await msg.edit_text("Uploaded.")
    else:
        await msg.edit_text("Failed to download.")

@app.post(f"/webhook/{BOT_TOKEN}")
async def webhook(req: Request):
    body = await req.json()
    update = Update.de_json(body, bot)
    asyncio.create_task(telegram_app.process_update(update))
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await bot.set_webhook(WEBHOOK_URL)