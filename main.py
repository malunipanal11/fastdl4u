from flask import Flask
import os
import threading
import logging
from bot import bot  # Your TeleBot instance

# Optional: Import if using a database
# from models import db, User, Download

# Setup logging
logging.basicConfig(level=logging.INFO)

# Get bot token (for debug print)
BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Using BOT_TOKEN:", BOT_TOKEN)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Optional DB setup
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)

@app.route('/')
def home():
    return "Bot is running!"

def start_bot():
    try:
        print("Starting polling from main.py...")
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")

# Start bot in a separate thread
bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
