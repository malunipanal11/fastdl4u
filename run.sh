#!/bin/bash
# Run both the web server and the Telegram bot
uvicorn backend.app:app --host 0.0.0.0 --port 8000 &
python3 backend/telegram_bot.py
