from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import asyncio
import os
from bot import register_handlers

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
register_handlers(dp)

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}
