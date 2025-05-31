main.py

from fastapi import FastAPI, Request from bot import start_bot import uvicorn

app = FastAPI()

@app.on_event("startup") async def startup_event(): await start_bot()

@app.get("/") async def root(): return {"message": "Telegram Bot is running!"}

if name == "main": uvicorn.run("main:app", host="0.0.0.0", port=8000)

