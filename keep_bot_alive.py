import os
import time
import subprocess
import logging
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_monitor.log"), logging.StreamHandler()]
)
logger = logging.getLogger("BotMonitor")

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found. Please set it in the environment.")
    exit(1)

logger.info("Bot monitor starting with token prefix: " + BOT_TOKEN[:5] + "...")

# Minimal Flask app to keep service alive
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080, use_reloader=False)

def start_bot_process():
    logger.info("Launching bot.py...")
    return subprocess.Popen(["python", "bot.py"])

def monitor_bot():
    while True:
        process = start_bot_process()
        process.wait()
        logger.warning(f"Bot exited with code {process.returncode}. Restarting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    logger.info("==== Bot Monitor Started ====")
    Thread(target=run_flask).start()
    try:
        monitor_bot()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("==== Bot Monitor Stopped ====")