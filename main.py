import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from contextlib import asynccontextmanager

from bot import register_handlers
from config import BOT_TOKEN, WEBHOOK_URL

# Logging
logging.basicConfig(level=logging.INFO)

# Setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
register_handlers(dp)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")
    yield
    await bot.delete_webhook()
    logging.info("🛑 Webhook deleted.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def handle_webhook(request: Request):
    update_data = await request.json()
    update = Update.model_validate(update_data)
    logging.info(f"📩 Received update: {update_data}")
    await dp.feed_update(bot, update)
    return {"ok": True}
