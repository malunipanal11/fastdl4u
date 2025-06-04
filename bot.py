import os
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# === CONFIG ===

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-service.onrender.com/webhook
ADMIN_IDS = [5558589142]  # Replace with your Telegram user ID
DB_PATH = "data/db.json"
CATEGORY_PATHS = {
    "images": "data/images",
    "videos": "data/videos",
    "audios": "data/audios",
    "files": "data/files",
    "text": "data/text"
}

# === UTILS ===

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

def get_next_serial():
    db = load_db()
    serial = str(len(db) + 1).zfill(4)
    return serial

def save_file(file_bytes, filename, category, extension):
    serial = get_next_serial()
    path = CATEGORY_PATHS[category]
    os.makedirs(path, exist_ok=True)
    full_filename = f"{serial}_{filename}.{extension}"
    full_path = os.path.join(path, full_filename)
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    db = load_db()
    db[serial] = {
        "file": full_filename,
        "category": category,
        "time": datetime.utcnow().isoformat()
    }
    save_db(db)
    return serial, full_path

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("Admin only.")
            return
        return await func(update, context)
    return wrapper

# === COMMAND HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and working!")

@admin_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Upload a file after using /add.")
        return

    doc = update.message.document
    ext = doc.file_name.split(".")[-1].lower()

    category = (
        "images" if ext in ["jpg", "png", "jpeg", "gif"] else
        "videos" if ext in ["mp4", "mov", "mkv"] else
        "audios" if ext in ["mp3", "ogg", "wav"] else
        "files" if ext in ["pdf", "zip", "rar"] else
        "text" if ext in ["txt", "md"] else None
    )

    if not category:
        await update.message.reply_text("Unsupported file type.")
        return

    file = await doc.get_file()
    file_bytes = await file.download_as_bytearray()
    serial, path = save_file(file_bytes, doc.file_name.rsplit('.', 1)[0], category, ext)

    await update.message.reply_text(f"Saved in /{category} with serial #{serial}")

async def send_from_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    files = os.listdir(CATEGORY_PATHS[category])
    if not files:
        await update.message.reply_text(f"No files in {category}.")
        return

    latest = sorted(files)[-1]
    path = os.path.join(CATEGORY_PATHS[category], latest)

    if category == "text":
        with open(path, "r") as f:
            sent = await update.message.reply_text(f.read())
    else:
        sent = await update.message.reply_document(open(path, "rb"))

    await asyncio.sleep(30)
    await update.message.delete()
    await asyncio.sleep(600)
    await sent.delete()

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, page: int = 0):
    files = sorted(os.listdir(CATEGORY_PATHS[category]))
    if not files:
        await update.message.reply_text("No files.")
        return

    start = page * 25
    end = start + 25
    keyboard = []

    for f in files[start:end]:
        serial = f.split("_")[0]
        btns = [
            InlineKeyboardButton("\U0001F4E5 Download", callback_data=f"download:{category}:{serial}"),
            InlineKeyboardButton("\u25B6\uFE0F Play", callback_data=f"play:{category}:{serial}"),
            InlineKeyboardButton("\U0001F4E4 Send", callback_data=f"send:{category}:{serial}")
        ]
        if update.effective_user.id in ADMIN_IDS:
            btns.append(InlineKeyboardButton("\u274C Delete", callback_data=f"delete:{category}:{serial}"))
        keyboard.append(btns)

    nav_btns = []
    if start > 0:
        nav_btns.append(InlineKeyboardButton("\u25C0\uFE0F Prev", callback_data=f"page:{category}:{page - 1}"))
    if end < len(files):
        nav_btns.append(InlineKeyboardButton("\u25B6\uFE0F Next", callback_data=f"page:{category}:{page + 1}"))
    if nav_btns:
        keyboard.append(nav_btns)

    await update.message.reply_text(
        f"List of {category} files (Page {page + 1})",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    action, category, serial = data.split(":") if not data.startswith("page") else data.split(":", 2)

    if action == "page":
        await list_files(query.message, context, category, int(serial))
        return

    path = None
    for fname in os.listdir(CATEGORY_PATHS[category]):
        if fname.startswith(serial):
            path = os.path.join(CATEGORY_PATHS[category], fname)
            break

    if not path or not os.path.exists(path):
        await query.message.reply_text("File not found.")
        return

    if action in ["download", "play", "send"]:
        await query.message.reply_document(InputFile(path))
    elif action == "delete" and query.from_user.id in ADMIN_IDS:
        os.remove(path)
        db = load_db()
        db.pop(serial, None)
        save_db(db)
        await query.message.reply_text(f"Deleted file #{serial} from {category}.")

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /get <serial>")
        return

    serial = context.args[0]
    db = load_db()
    if serial not in db:
        await update.message.reply_text("Serial not found.")
        return

    meta = db[serial]
    if meta["category"] not in ["files", "text"]:
        await update.message.reply_text("/get only allowed for files or text category.")
        return

    path = os.path.join(CATEGORY_PATHS[meta["category"]], meta["file"])
    if meta["category"] == "text":
        with open(path, "r") as f:
            await update.message.reply_text(f.read())
    else:
        await update.message.reply_document(open(path, "rb"))

# === FASTAPI + TELEGRAM APP ===

application = Application.builder().token(TOKEN).build()

# === Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("images", lambda u, c: send_from_category(u, c, "images")))
application.add_handler(CommandHandler("videos", lambda u, c: send_from_category(u, c, "videos")))
application.add_handler(CommandHandler("audios", lambda u, c: send_from_category(u, c, "audios")))
application.add_handler(CommandHandler("files", lambda u, c: send_from_category(u, c, "files")))
application.add_handler(CommandHandler("text", lambda u, c: send_from_category(u, c, "text")))

application.add_handler(CommandHandler("imglist", lambda u, c: list_files(u, c, "images")))
application.add_handler(CommandHandler("vidlist", lambda u, c: list_files(u, c, "videos")))
application.add_handler(CommandHandler("audlist", lambda u, c: list_files(u, c, "audios")))
application.add_handler(CommandHandler("fileslist", lambda u, c: list_files(u, c, "files")))
application.add_handler(CommandHandler("textlist", lambda u, c: list_files(u, c, "text")))

application.add_handler(CommandHandler("get", get_file))
application.add_handler(CallbackQueryHandler(handle_cb))

# === FastAPI Lifespan ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    print("Webhook received:", json.dumps(data, indent=2))  # Optional debug
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
