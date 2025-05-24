import os
import re
import json
import time
import requests
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import yt_dlp

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found.")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramBot")

# Supported domains
SUPPORTED_DOMAINS = [
    "youtube.com", "youtu.be", "instagram.com", "facebook.com",
    "twitter.com", "tiktok.com", "vimeo.com", "soundcloud.com",
    "dailymotion.com", "terabox.com", "4funbox.com"
]

def is_supported_platform(url):
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def is_terabox_link(url):
    return re.match(r"https?://(www\.)?(terabox|4funbox)\.com/s/\w+", url)

def get_terabox_info(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        match = re.search(r'window\.preData\s*=\s*(\{.*?\});', response.text)
        if match:
            data = json.loads(match.group(1))
            file = data.get("file_list", {}).get("list", [{}])[0]
            return {
                "name": file.get("server_filename"),
                "size": round(int(file.get("size", 0)) / 1024 / 1024, 2),
                "download_url": f"https://www.terabox.com/share/download?surl={data.get('shareid')}"
            }
    except Exception as e:
        logger.error(f"TeraBox error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a video or TeraBox link to begin.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_supported_platform(url):
        await update.message.reply_text(
            "❌ Unsupported platform.\nSupported: YouTube, Instagram, Facebook, Twitter, TikTok, Vimeo, SoundCloud, Dailymotion, and TeraBox."
        )
        return

    if is_terabox_link(url):
        await update.message.reply_text("📦 Fetching TeraBox file info...")
        info = get_terabox_info(url)
        if info:
            await update.message.reply_text(
                f"**File:** {info['name']}\n"
                f"**Size:** {info['size']} MB\n"
                f"[Download Now]({info['download_url']})",
                parse_mode="Markdown", disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("❌ Could not get TeraBox file info.")
        return

    msg = await update.message.reply_text("🔍 Analyzing link...")
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title", "Unknown")
        duration = info.get("duration_string") or f"{info.get('duration', 0)} sec"
        platform = info.get("extractor_key")
        thumbnail = info.get("thumbnail")

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Video 🎬", callback_data=f"video|{url}")],
            [InlineKeyboardButton("Audio 🎧", callback_data=f"audio|{url}")]
        ])

        await msg.delete()
        await update.message.reply_photo(
            photo=thumbnail,
            caption=f"*{title}*\nPlatform: {platform}\nDuration: {duration}",
            parse_mode="Markdown",
            reply_markup=buttons
        )

    except Exception as e:
        logger.error(f"yt-dlp error: {e}")
        await msg.edit_text(
            "❌ I couldn’t download this. Please make sure the link is public and supported.\n\n"
            "Supported platforms: YouTube, Instagram, Facebook, Twitter, TikTok, Vimeo, SoundCloud, Dailymotion, and TeraBox."
        )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, url = query.data.split('|')
    file_name = f"temp_{int(time.time())}"
    output = f"{file_name}.mp4" if action == "video" else f"{file_name}.mp3"

    msg = await query.message.reply_text("⬇️ Downloading...")

    def progress_hook(d):
        if d['status'] == 'downloading':
            pct = d.get('_percent_str', '0%').strip()
            context.application.create_task(msg.edit_text(f"Downloading: {pct}"))

    ydl_opts = {
        'outtmpl': output,
        'format': 'best' if action == 'video' else 'bestaudio',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if action == 'audio' else [],
        'progress_hooks': [progress_hook],
        'noplaylist': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await msg.edit_text("📤 Uploading...")

        with open(output, 'rb') as f:
            upload = requests.post("https://store1.gofile.io/uploadFile", files={'file': f})
        result = upload.json()
        dl_url = result['data']['downloadPage']

        await msg.edit_text(f"✅ Done: [Download Now]({dl_url})", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await msg.edit_text("❌ Failed. Try another link.")
    finally:
        if os.path.exists(output):
            os.remove(output)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
