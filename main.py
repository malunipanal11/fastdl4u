import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, WEBHOOK_DOMAIN
from handlers import router

# Set your webhook path like: https://yourdomain.com/webhook/{token}
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Create bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


async def on_startup(bot: Bot) -> None:
    webhook_url = f"{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    print(f"🚀 Webhook set: {webhook_url}")


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    print("🛑 Webhook deleted")


async def main():
    app = web.Application()
    app["bot"] = bot

    setup_application(app, dp, bot, path=WEBHOOK_PATH)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return app


if __name__ == "__main__":
    web.run_app(main(), host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
