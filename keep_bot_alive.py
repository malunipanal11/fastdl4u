import os
import time
import signal
import subprocess
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BotMonitor")

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables. Please check your .env file.")
    exit(1)

logger.info("Bot monitor starting with token: " + BOT_TOKEN[:5] + "...")

def start_bot_process():
    """Start the bot process and return the process object."""
    logger.info("Starting bot process...")
    return subprocess.Popen(["python", "bot.py"])

def monitor_bot():
    """Monitor the bot and restart it if it crashes."""
    while True:
        # Start the bot
        process = start_bot_process()
        
        # Wait for it to finish or crash
        process.wait()
        
        # If we get here, the bot has stopped
        exit_code = process.returncode
        logger.warning(f"Bot process exited with code {exit_code}, restarting in 5 seconds...")
        
        # Wait before restarting
        time.sleep(5)

if __name__ == "__main__":
    logger.info("==== 24/7 Bot Monitor Started ====")
    try:
        monitor_bot()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
    finally:
        logger.info("==== Bot Monitor Stopped ====")