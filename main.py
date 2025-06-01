import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import register_handlers  # Your router logic
from config import TOKEN, WEBHOOK_URL  # ✅ Corrected import

# Initialize bot, dispatcher, FastAPI app
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# Register message/callback handlers
register_handlers(dp)

# Webhook handler
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp._process_update(update)
    return {"ok": True}

# Set webhook on startup
@app.on_event("startup")
async def on_startup():
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL not set.")
        return
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set to: {WEBHOOK_URL}")

# Optional cleanup on shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("Webhook deleted.")
