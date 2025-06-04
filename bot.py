import os
import logging
from uuid import uuid4
from typing import Dict, List, Tuple

import httpx
from fastapi import FastAPI, Request
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, Application,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL env variable")

app = FastAPI()
upload_mode_users = set()

FILE_DB: Dict[str, List[Tuple[str, str]]] = {
    "images": [],
    "documents": [],
    "videos": [],
    "audios": [],
    "texts": []
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ---------- Gofile Upload ----------
def get_gofile_server():
    response = httpx.get("https://api.gofile.io/getServer")
    return response.json()["data"]["server"]

def upload_to_gofile(filepath):
    server = get_gofile_server()
    with open(filepath, "rb") as f:
        files = {"file": f}
        res = httpx.post(f"https://{server}.gofile.io/uploadFile", files=files)
    if res.status_code == 200:
        return res.json()["data"]["downloadPage"]
    return None

# ---------- Telegram Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upload_mode_users.add(update.effective_user.id)
    await update.message.reply_text("✅ Upload mode ON. Send files or text.\nWhen done, send /done.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upload_mode_users.discard(update.effective_user.id)
    await update.message.reply_text("✅ Upload mode OFF.")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text[1:]
    category = FILE_DB.get(cmd)
    if not category:
        await update.message.reply_text(f"❌ No {cmd} uploaded yet.")
        return

    for name, url in category:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Download", url=url)]])
        if cmd == "images":
            await update.message.reply_photo(photo=url, caption=name, reply_markup=keyboard)
        elif cmd == "videos":
            await update.message.reply_video(video=url, caption=name, reply_markup=keyboard)
        elif cmd == "audios":
            await update.message.reply_audio(audio=url, caption=name, reply_markup=keyboard)
        else:
            await update.message.reply_text(f"{name}\n{url}")

# ---------- Handle Files/Text ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in upload_mode_users:
        await update.message.reply_text("❌ Please use /add before sending files.")
        return

    file_type = None
    tg_file = None
    name = None

    if update.message.photo:
        tg_file = update.message.photo[-1]
        file_type = 'images'
        name = f"photo_{uuid4().hex[:8]}.jpg"
    elif update.message.document:
        tg_file = update.message.document
        file_type = 'documents'
        name = tg_file.file_name or f"doc_{uuid4().hex[:8]}"
    elif update.message.video:
        tg_file = update.message.video
        file_type = 'videos'
        name = f"video_{uuid4().hex[:8]}.mp4"
    elif update.message.audio or update.message.voice:
        tg_file = update.message.audio or update.message.voice
        file_type = 'audios'
        name = f"audio_{uuid4().hex[:8]}.mp3"
    elif update.message.text:
        content = update.message.text
        file_type = 'texts'
        name = f"text_{uuid4().hex[:8]}.txt"
        with open(name, 'w') as f:
            f.write(content)
        gofile_link = upload_to_gofile(name)
        os.remove(name)
        if gofile_link:
            FILE_DB.setdefault(file_type, []).append((name, gofile_link))
            await update.message.reply_text(f"✅ Text saved: {gofile_link}")
        else:
            await update.message.reply_text("❌ Failed to upload text.")
        return
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    file = await context.bot.get_file(tg_file.file_id)
    local_path = f"temp_{name}"
    await file.download_to_drive(local_path)

    gofile_link = upload_to_gofile(local_path)
    os.remove(local_path)

    if gofile_link:
        FILE_DB.setdefault(file_type, []).append((name, gofile_link))
        logger.info(f"File uploaded: {file_type} - {name} - {gofile_link}")
        await update.message.reply_text(
            f"✅ File saved in /{file_type} as #{len(FILE_DB[file_type]):04d}\n{gofile_link}"
        )
    else:
        await update.message.reply_text("❌ Upload failed.")

# ---------- Telegram App Initialization ----------
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("done", done))

for cmd in FILE_DB.keys():
    application.add_handler(CommandHandler(cmd, list_files))

application.add_handler(MessageHandler(filters.ALL, handle_file))

# ---------- FastAPI Webhook ----------
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def startup_event():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await application.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("add", "Enable upload mode"),
        BotCommand("done", "Disable upload mode"),
        BotCommand("images", "List uploaded images"),
        BotCommand("documents", "List uploaded documents"),
        BotCommand("videos", "List uploaded videos"),
        BotCommand("audios", "List uploaded audios"),
        BotCommand("texts", "List uploaded texts"),
    ])
    logger.info("✅ Webhook and commands registered.")
