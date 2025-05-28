import os
import json
import re
import requests
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Replace with your bot token
BOT_TOKEN = "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw"

# Ensure download folder exists
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def save_log(data):
    log = []
    if os.path.exists("file_log.json"):
        with open("file_log.json", "r") as f:
            try:
                log = json.load(f)
            except:
                pass
    log.append(data)
    with open("file_log.json", "w") as f:
        json.dump(log, f, indent=2)

def download_youtube(url):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title).200B.%(ext)s',
        'format': 'best',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath, info.get("title")

def is_terabox_link(url):
    return "terabox" in url

def is_twitter_link(url):
    return "twitter.com" in url

def is_threads_link(url):
    return "threads.net" in url

def is_pinterest_link(url):
    return "pinterest.com" in url

def fallback_download(url):
    # Replace this with your API logic for Terabox, Twitter, Threads, Pinterest
    filename = re.sub(r'\W+', '_', url) + ".txt"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    with open(path, "w") as f:
        f.write(f"Manual download required: {url}")
    return path, "Manual Download"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a video link (YouTube, Twitter, Terabox, Threads, Pinterest) and I will try to download it.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing...")
    try:
        if is_terabox_link(url) or is_twitter_link(url) or is_threads_link(url) or is_pinterest_link(url):
            path, title = fallback_download(url)
        else:
            path, title = download_youtube(url)

        await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))
        save_log({"title": title, "file": os.path.basename(path), "url": url})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()
