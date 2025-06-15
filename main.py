from fastapi import FastAPI, Request
from bot_commands import handle_telegram_update

app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    return await handle_telegram_update(data)
