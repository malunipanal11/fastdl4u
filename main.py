import os, json, re, requests
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
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
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath, info.get("title")

def is_terabox_link(url):
    return any(domain in url for domain in ["terabox.com", "1024terabox.com"])

def is_supported_link(url):
    supported_domains = ["youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "soundcloud.com", "dailymotion.com", "twitch.tv", "reddit.com"]
    return any(domain in url for domain in supported_domains)

def resolve_terabox_video(url):
    try:
        api_url = "https://terabox-api.vercel.app/api"
        response = requests.get(api_url, params={"link": url}, timeout=10)
        data = response.json()

        if not data.get("success") or "download_url" not in data:
            raise Exception("Failed to resolve video")

        file_url = data["download_url"]
        title = data.get("title", "terabox_video")
        ext = file_url.split(".")[-1].split("?")[0]
        safe_title = re.sub(r"[^\w\-_. ]", "_", title)
        filename = f"{safe_title}.{ext}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        file_data = requests.get(file_url)
        with open(filepath, "wb") as f:
            f.write(file_data.content)

        return filepath, title

    except Exception:
        return fallback_download(url)

def fallback_download(url):
    filename = re.sub(r'\W+', '_', url)[:50] + ".txt"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    with open(path, "w") as f:
        f.write(f"Manual download required: {url}")
    return path, "Manual Download"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a video link (YouTube, Vimeo, TikTok, SoundCloud, Reddit, Terabox, etc.) and I will try to download it.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing...")
    try:
        if is_terabox_link(url):
            path, title = resolve_terabox_video(url)
        elif is_supported_link(url):
            path, title = download_youtube(url)
        else:
            path, title = fallback_download(url)

        await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))
        save_log({"title": title, "file": os.path.basename(path), "url": url})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    webhook_url = os.getenv("WEBHOOK_URL")
    await Bot(BOT_TOKEN).set_webhook(webhook_url)
    yield
    await telegram_app.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, Bot(BOT_TOKEN))
    await telegram_app.update_queue.put(update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
