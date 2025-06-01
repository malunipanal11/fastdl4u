import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from handlers import register_handlers
from config import TOKEN, WEBHOOK_URL

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# FastAPI app
app = FastAPI()

# Register handlers
register_handlers(dp)

# Webhook endpoint
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp._process_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"ok": False}

# Startup: set webhook
@app.on_event("startup")
async def on_startup():
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL not set.")
        return
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")

# Shutdown: delete webhook
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("🛑 Webhook deleted.")
