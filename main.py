from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import TOKEN, WEBHOOK_URL
from handlers import router

# Define bot and dispatcher
bot = Bot(token=TOKEN, default=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Define FastAPI app
app = FastAPI()

# Webhook setup
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

# Handle webhook requests
@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    return await SimpleRequestHandler(dispatcher=dp, bot=bot).handle(request)
