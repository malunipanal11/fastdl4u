from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from downloader import download_all_assets
from telegram_bot import telegram_webhook
import os, json

# Ensure folders exist
os.makedirs("static/videos", exist_ok=True)

app = FastAPI()

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

VIDEO_DB = "static/videos/metadata.json"

def load_videos():
    try:
        if os.path.exists(VIDEO_DB):
            with open(VIDEO_DB, 'r') as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Failed to load metadata: JSON is invalid")
    return []

def save_video(info):
    data = load_videos()
    data.append(info)
    with open(VIDEO_DB, 'w') as f:
        json.dump(data, f)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    videos = load_videos()
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.post("/download")
async def download_link(link: str = Form(...)):
    meta = download_all_assets(link)
    if meta:
        save_video(meta)
        return {"status": "ok", "meta": meta}
    else:
        return {"status": "error", "message": "Download failed"}

@app.post("/webhook")
async def handle_telegram_webhook(request: Request):
    return await telegram_webhook(request)
