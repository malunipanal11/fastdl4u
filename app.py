from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from downloader import download_all_assets
import os
import json

# Ensure video directory exists
os.makedirs("static/videos", exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

VIDEO_DB = "static/videos/metadata.json"

def load_videos():
    if os.path.exists(VIDEO_DB):
        with open(VIDEO_DB, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_video(info):
    data = load_videos()
    data.append(info)
    with open(VIDEO_DB, 'w') as f:
        json.dump(data, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    videos = load_videos()
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.post("/download")
async def download_link(link: str = Form(...)):
    meta = download_all_assets(link)
    save_video(meta)
    return {"status": "ok", "meta": meta}
