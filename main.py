from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, WEBHOOK_URL
from handlers import router

# Create bot with default HTML parse mode
bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

app = web.Application()

# Webhook setup on app startup
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

app.on_startup.append(on_startup)

# Register request handler with dispatcher and bot
setup_application(app, dp, bot=bot)
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")

# Export app for uvicorn
# Command to run: uvicorn main:app --host 0.0.0.0 --port $PORT
