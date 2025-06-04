import os
import logging
import aiohttp
import glob
from uuid import uuid4
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import atexit

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Should end in /webhook

GOFILE_API = f"https://api.gofile.io/uploadFile?token={GOFILE_TOKEN}"
logging.basicConfig(level=logging.INFO)

FILE_DB = {}
upload_mode_users = set()

# FastAPI app
app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Cleanup temp files on exit
def cleanup_temp_files():
    for file in glob.glob("temp_*"):
        try:
            os.remove(file)
        except Exception:
            pass
atexit.register(cleanup_temp_files)

# Upload to GoFile
async def upload_to_gofile(file_path):
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=os.path.basename(file_path))
            async with session.post(GOFILE_API, data=data) as resp:
                res_json = await resp.json()
                if res_json.get('status') == 'ok':
                    return res_json['data']['downloadPage']
    return None

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready!")

# /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upload_mode_users.add(user_id)
    await update.message.reply_text("✅ Upload mode ON. Send files or text.\nWhen done, send /done.")

# /done
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in upload_mode_users:
        upload_mode_users.discard(user_id)
        await update.message.reply_text("✅ Upload mode OFF.")
    else:
        await update.message.reply_text("ℹ️ You were not in upload mode.")

# File/Text handler
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in upload_mode_users:
        await update.message.reply_text("❌ Use /add before sending files.")
        return

    file_type = None
    tg_file = None
    name = None

    # Detect type
    if update.message.document:
        tg_file = update.message.document
        file_type = 'documents'
    elif update.message.photo:
        tg_file = update.message.photo[-1]
        file_type = 'images'
    elif update.message.video:
        tg_file = update.message.video
        file_type = 'videos'
    elif update.message.audio:
        tg_file = update.message.audio
        file_type = 'audios'
    elif update.message.voice:
        tg_file = update.message.voice
        file_type = 'audios'
    elif update.message.text:
        content = update.message.text
        file_type = 'texts'
        name = f"text_{uuid4().hex[:8]}.txt"
        with open(name, 'w') as f:
            f.write(content)
        gofile_link = await upload_to_gofile(name)
        os.remove(name)
        if gofile_link:
            FILE_DB.setdefault(file_type, []).append((name, gofile_link))
            await update.message.reply_text(f"✅ Text saved:\n{gofile_link}")
        else:
            await update.message.reply_text("❌ Failed to upload text.")
        return

    if not tg_file:
        await update.message.reply_text("❌ Unsupported or empty file.")
        return

    file = await context.bot.get_file(tg_file.file_id)
    name = getattr(tg_file, 'file_name', f"{file_type}_{uuid4().hex[:8]}")
    local_path = f"temp_{name}"
    await file.download_to_drive(local_path)

    gofile_link = await upload_to_gofile(local_path)
    os.remove(local_path)

    if gofile_link:
        FILE_DB.setdefault(file_type, []).append((name, gofile_link))
        await update.message.reply_text(f"✅ File saved as #{len(FILE_DB[file_type]):04d} in /{file_type}\n{gofile_link}")
    else:
        await update.message.reply_text("❌ Upload failed.")

# /files - list all
async def list_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FILE_DB:
        await update.message.reply_text("❌ No files uploaded yet.")
        return

    message = "📂 ALL FILES:\n\n"
    for ftype, items in FILE_DB.items():
        message += f"🔸 {ftype.upper()}:\n"
        for i, (name, link) in enumerate(items, 1):
            message += f"#{i:04d} - {name}: {link}\n"
        message += "\n"
    await update.message.reply_text(message, disable_web_page_preview=True)

# /images /videos etc
async def list_by_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_type = update.message.text[1:]
    files = FILE_DB.get(file_type, [])
    if not files:
        await update.message.reply_text(f"❌ No {file_type} uploaded yet.")
    else:
        message = f"📁 {file_type.upper()}:\n\n"
        for i, (name, link) in enumerate(files, 1):
            message += f"#{i:04d} - {name}: {link}\n"
        await update.message.reply_text(message, disable_web_page_preview=True)

# Commands
async def set_bot_commands(app):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("add", "Enter upload mode"),
        BotCommand("done", "Exit upload mode"),
        BotCommand("files", "List all uploaded files"),
        BotCommand("images", "List uploaded images"),
        BotCommand("videos", "List uploaded videos"),
        BotCommand("audios", "List uploaded audios"),
        BotCommand("texts", "List uploaded texts"),
    ]
    await app.bot.set_my_commands(commands)

# Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("add", add))
telegram_app.add_handler(CommandHandler("done", done))
telegram_app.add_handler(CommandHandler("files", list_all_files))
telegram_app.add_handler(CommandHandler("images", list_by_type))
telegram_app.add_handler(CommandHandler("videos", list_by_type))
telegram_app.add_handler(CommandHandler("audios", list_by_type))
telegram_app.add_handler(CommandHandler("texts", list_by_type))
telegram_app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_file))

# FastAPI startup
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    await set_bot_commands(telegram_app)
    logging.info("✅ Webhook set and bot commands registered.")

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True"}
