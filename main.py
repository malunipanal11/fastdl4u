import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from bot import register_handlers  # You should define this in bot.py

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Should be your Render service URL + /webhook

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Register all handlers from your bot logic
register_handlers(dp)

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    update_data = await request.json()
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set.")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("Webhook deleted.")
