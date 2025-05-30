import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv

from bot.handlers import (
    start, handle_add, handle_get,
    handle_list, handle_request,
    handle_approve, handle_deny
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("add", handle_add))
telegram_app.add_handler(CommandHandler("get", handle_get))
telegram_app.add_handler(CommandHandler("list", handle_list))
telegram_app.add_handler(CommandHandler("request", handle_request))
telegram_app.add_handler(CommandHandler("approve", handle_approve))
telegram_app.add_handler(CommandHandler("deny", handle_deny))

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return JSONResponse(content={"ok": True})
