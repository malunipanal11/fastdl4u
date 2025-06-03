import os
import random
import sqlite3
import aiohttp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from fastapi import FastAPI, Request

# --- Load environment variables ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")  # example: https://your-app-name.onrender.com

# --- Database Setup ---
conn = sqlite3.connect("files.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        serial INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        file_type TEXT,
        gofile_link TEXT,
        tg_file_id TEXT
    )
""")
conn.commit()

# --- Async GoFile Upload Function ---
async def upload_to_gofile(file_bytes, file_name):
    url = "https://api.gofile.io/uploadFile"
    data = aiohttp.FormData()
    data.add_field('file', file_bytes, filename=file_name)
    params = {"token": GOFILE_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, params=params) as resp:
            resp.raise_for_status()
            json_resp = await resp.json()
            return json_resp["data"]["downloadPage"]

# --- Helper Function ---
def detect_file_type(file_name, mime_type):
    ext = file_name.lower().split('.')[-1]
    if ext in ["jpg", "jpeg", "png", "gif"]:
        return "image"
    if ext in ["mp4", "avi", "mov"]:
        return "video"
    if ext in ["mp3", "wav", "ogg"]:
        return "audio"
    if ext in ["pdf", "txt"]:
        return "text"
    if ext in ["url", "link"]:
        return "link"
    return "other"

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Telegram Storage Bot!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Please send a file with this command.")
        return
    file = update.message.document
    file_name = file.file_name or f"file_{file.file_id}"
    file_type = detect_file_type(file_name, file.mime_type)
    tg_file = await context.bot.get_file(file.file_id)
    file_bytes = await tg_file.download_as_bytearray()
    gofile_link = await upload_to_gofile(file_bytes, file_name)

    cur.execute(
        "INSERT INTO files (file_name, file_type, gofile_link, tg_file_id) VALUES (?, ?, ?, ?)",
        (file_name, file_type, gofile_link, file.file_id)
    )
    conn.commit()
    serial = cur.lastrowid
    await update.message.reply_text(f"File uploaded! Serial: {serial}")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lstrip("/").replace("list", "")
    typemap = {"img": "image", "vid": "video", "aud": "audio", "text": "text", "link": "link"}
    file_type = typemap.get(cmd)

    cur.execute("SELECT serial, file_name, gofile_link FROM files WHERE file_type=?", (file_type,))
    files = cur.fetchall()
    if not files:
        await update.message.reply_text("No files found.")
        return
    for serial, name, link in files:
        kb = [
            [InlineKeyboardButton("Download", url=link),
             InlineKeyboardButton("Delete", callback_data=f"del_{serial}")]
        ]
        await update.message.reply_text(f"{serial}: {name}", reply_markup=InlineKeyboardMarkup(kb))

async def delete_later(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)

async def random_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lstrip("/").replace("s", "")
    cur.execute("SELECT serial, gofile_link FROM files WHERE file_type=?", (cmd,))
    files = cur.fetchall()
    if not files:
        await update.message.reply_text("No files found.")
        return
    serial, link = random.choice(files)
    msg = await update.message.reply_text(f"Random file: {link} (serial: {serial})")
    await context.job_queue.run_once(delete_later, 600, data=msg.message_id, chat_id=msg.chat_id)

async def get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /get <serial>")
        return
    serial = int(context.args[0])
    cur.execute("SELECT gofile_link FROM files WHERE serial=?", (serial,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text("File not found.")
        return
    msg = await update.message.reply_text(f"File: {row[0]}")
    await context.job_queue.run_once(delete_later, 1800, data=msg.message_id, chat_id=msg.chat_id)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith("del_"):
        serial = int(query.data.split("_")[1])
        cur.execute("DELETE FROM files WHERE serial=?", (serial,))
        conn.commit()
        await query.edit_message_text("File deleted.")

# --- FastAPI & Application ---
app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("add", add))

for cmd in ["imglist", "vidlist", "audlist", "textlist", "linklist"]:
    bot_app.add_handler(CommandHandler(cmd, list_files))

for cmd in ["images", "videos", "audio"]:
    bot_app.add_handler(CommandHandler(cmd, random_file))

bot_app.add_handler(CommandHandler("get", get))
bot_app.add_handler(CallbackQueryHandler(button))

@app.on_event("startup")
async def on_startup():
    bot = Bot(token=TOKEN)
    await bot.set_webhook(f"{WEBHOOK_DOMAIN}/webhook")

@app.post("/webhook")
async def handle_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
