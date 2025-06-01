import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from starlette.responses import JSONResponse

from config import TOKEN, WEBHOOK_URL
from handlers import register_handlers
from gofile import load_from_disk, save_to_disk

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Initialize FastAPI app
app = FastAPI()

# Register bot command/message handlers
register_handlers(dp)

# Load persisted data on startup
@app.on_event("startup")
async def on_startup():
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL not set.")
        return

    # Load GoFile state from disk
    load_from_disk()

    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")


# Clean shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    save_to_disk()
    logging.info("🛑 Webhook deleted. Data saved.")


# Webhook endpoint for Telegram
@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp._process_update(bot=bot, update=update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return JSONResponse(content={"ok": False}, status_code=500)
