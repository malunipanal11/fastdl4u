# main.py

import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router
from config import BOT_TOKEN

# Logging
logging.basicConfig(level=logging.INFO)

# Initialize bot & dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Initialize FastAPI app
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data)
    logging.info("Received Telegram update")
    await dp._process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logging.warning("WEBHOOK_URL not set.")
        return
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("Webhook deleted.")
