import os
import asyncio
import random
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)

from bot.handlers import (
    start, handle_add, handle_list, handle_get,
    handle_request, handle_approve, handle_deny
)
from bot.mega_utils import MegaUploader

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Initialize Mega uploader
uploader = MegaUploader()

# FastAPI app
app = FastAPI()
app_state = {
    "requests": {},
    "shared_files": {}  # code: {"file": file_path, "expiry": timestamp, "user": user_id}
}

# Bot Setup
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Register command handlers
telegram_app.add_handler(CommandHandler("start", start(app_state, ADMIN_ID)))
telegram_app.add_handler(CommandHandler("add", handle_add(app_state, uploader, DOWNLOAD_FOLDER, ADMIN_ID)))
telegram_app.add_handler(CommandHandler("list", handle_list(app_state, ADMIN_ID)))
telegram_app.add_handler(CommandHandler("get", handle_get(app_state)))
telegram_app.add_handler(CommandHandler("request", handle_request(app_state)))
telegram_app.add_handler(CommandHandler("approve", handle_approve(app_state)))
telegram_app.add_handler(CommandHandler("deny", handle_deny(app_state)))

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return JSONResponse(content={"ok": True})
