import os, json, re, requests
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # must be set in Render
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app = FastAPI()

# Save logs
def save_log(data):
    log = []
    if os.path.exists("file_log.json"):
        try:
            with open("file_log.json", "r") as f:
                log = json.load(f)
        except:
            pass
    log.append(data)
    with open("file_log.json", "w") as f:
        json.dump(log, f, indent=2)

# Check Terabox
def is_terabox_link(url):
    return any(domain in url for domain in ["terabox.com", "1024terabox.com"])

# Supported video platforms
def is_supported_link(url):
    supported = ["youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "soundcloud.com", "dailymotion.com", "twitch.tv", "reddit.com"]
    return any(domain in url for domain in supported)

# Fallback text
def fallback_download(url):
    filename = re.sub(r'\W+', '_', url)[:50] + ".txt"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    with open(path, "w") as f:
        f.write(f"Manual download required: {url}")
    return path, "Manual Download"

# YouTube & others
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

# ✅ Updated working Terabox API
def resolve_terabox_video(url):
    try:
        api_url = "https://teraboxdrivelink.vercel.app/api"
        response = requests.get(api_url, params={"link": url}, timeout=15)
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

        return filepath, title, file_url
    except Exception as e:
        print(f"TeraBox API failed: {e}")
        return fallback_download(url) + (None,)

# Telegram /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send a video link (YouTube, Terabox, etc.) to download.")

# Telegram message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing...")

    try:
        if is_terabox_link(url):
            path, title, _ = resolve_terabox_video(url)
        elif is_supported_link(url):
            path, title = download_youtube(url)
        else:
            path, title = fallback_download(url)

        await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))
        save_log({"title": title, "file": os.path.basename(path), "url": url})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Telegram app
telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Telegram webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, Bot(BOT_TOKEN))
    await telegram_app.update_queue.put(update)
    return {"ok": True}

# API endpoint for link resolver
@app.get("/api")
async def api_resolver(link: str):
    try:
        _, title, file_url = resolve_terabox_video(link)
        if file_url:
            return JSONResponse({"success": True, "download_url": file_url, "title": title})
        else:
            return JSONResponse({"success": False, "error": "Manual download required"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

# App lifecycle
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.start()
    if WEBHOOK_URL:
        try:
            await Bot(BOT_TOKEN).set_webhook(WEBHOOK_URL)
        except Exception as e:
            print(f"Webhook setup error: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.stop()

# Run Uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
