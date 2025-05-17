from flask import Flask
import os
import threading
import logging
from bot import bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Using BOT_TOKEN:", BOT_TOKEN)

def start_bot():
    try:
        print("Starting bot polling...")
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")

bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
