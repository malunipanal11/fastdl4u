import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from contextlib import asynccontextmanager
from bot import register_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

print("🔐 BOT_TOKEN:", BOT_TOKEN)
print("🌐 WEBHOOK_URL:", WEBHOOK_URL)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

register_handlers(dp)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook set to:", WEBHOOK_URL)
    yield
    await bot.delete_webhook()
    print("🛑 Webhook deleted.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data)
        print("📩 Received update:", update_data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("❌ Error processing update:", str(e))
        return {"ok": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
