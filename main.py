from flask import Flask
import os
import threading
import logging
from bot import bot  # Import the TeleBot instance from bot.py

# Setup logging
logging.basicConfig(level=logging.INFO)

# Print bot token for verification
BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Using BOT_TOKEN:", BOT_TOKEN)

# Flask app for Render health check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def start_bot():
    try:
        print("Starting polling from main.py...")
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")

# Run the bot in a separate thread
bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
