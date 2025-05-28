# main.py
import os, json, asyncio, re, requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from yt_dlp import YoutubeDL

BOT_TOKEN = "YOUR_BOT_TOKEN"
WEBHOOK_URL = f"https://yourdomain.com/webhook/{BOT_TOKEN}"
DOWNLOAD_FOLDER = "downloads"
JSON_LOG = "file_log.json"

app = FastAPI()
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads")
templates = Jinja2Templates(directory="templates")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
bot = Bot(token=BOT_TOKEN)
telegram_app = Application.builder().token(BOT_TOKEN).build()

def save_log(data):
    log = []
    if os.path.exists(JSON_LOG):
        with open(JSON_LOG, "r") as f:
            try:
                log = json.load(f)
            except: pass
    log.append(data)
    with open(JSON_LOG, "w") as f:
        json.dump(log, f, indent=2)

def download_video(url: str):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title).200B.%(ext)s',
        'format': 'best',
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath, info.get("title")

def is_terabox_link(url):
    return any(p in url for p in ["terabox.com", "1024terabox.com"])

def resolve_terabox_link(url):
    match = re.search(r"/s/([^/?#]+)", url)
    if not match:
        raise Exception("Invalid Terabox link format.")
    share_id = match.group(1)
    # Dummy fallback file
    filename = f"{share_id}.txt"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    with open(path, "w") as f:
        f.write(f"Download manually from: {url}")
    return path, "Manual Download Link"

# Telegram Bot Handlers
async def start(update: Update, context):
    await update.message.reply_text("📥 Send me a link from YouTube, Terabox, etc. and I will download it.")

async def handle_message(update: Update, context):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ Processing...")
    try:
        if is_terabox_link(url):
            path, title = resolve_terabox_link(url)
        else:
            path, title = download_video(url)

        await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))
        save_log({"title": title, "file": os.path.basename(path), "url": f"/downloads/{os.path.basename(path)}"})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    files = []
    try:
        with open(JSON_LOG, "r") as f:
            files = json.load(f)
    except: pass
    return templates.TemplateResponse("index.html", {"request": request, "files": files})

@app.post("/api/download")
async def api_download(request: Request):
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
    try:
        if is_terabox_link(url):
            path, title = resolve_terabox_link(url)
        else:
            path, title = download_video(url)
        file_url = f"/downloads/{os.path.basename(path)}"
        save_log({"title": title, "file": os.path.basename(path), "url": file_url})
        return {"success": True, "file_url": file_url, "title": title}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/play/{filename}", response_class=FileResponse)
async def play_file(filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("File not found", status_code=404)

@app.get("/delete/{filename}")
async def delete_file(filename: str):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return HTMLResponse("Deleted", status_code=200)

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return HTMLResponse("Forbidden", status_code=403)
    data = await request.json()
    update = Update.de_json(data, bot)
    await telegram_app.update_queue.put(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)