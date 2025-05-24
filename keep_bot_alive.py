import os
import time
import subprocess
import logging
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_monitor.log"), logging.StreamHandler()]
)
logger = logging.getLogger("BotMonitor")

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found.")
    exit(1)

logger.info("Bot monitor starting with token: " + BOT_TOKEN[:5] + "...")

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
        logger.warning(f"Bot crashed. Restarting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    logger.info("==== Bot Monitor Started ====")
    Thread(target=run_flask).start()
    try:
        monitor_bot()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
    finally:
        logger.info("==== Bot Monitor Stopped ====")
