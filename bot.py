# --- Render Free Web Service PORT Fix (bind simple HTTP health) ---
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()
# ------------------------------------------------------------------

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified
import re
import subprocess
import requests
import shutil

from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "multi_link_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# URL detection
URL_RE = r"(https?://[^\s]+)"

# Normalize known platforms when helpful
def normalize_url(url: str) -> str:
    # Normalize YouTube Shorts to watch?v=
    # Example: https://youtube.com/shorts/ID -> https://www.youtube.com/watch?v=ID
    m = re.search(r"(https?://(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]+))", url)
    if m:
        vid = m.group(2)
        return f"https://www.youtube.com/watch?v={vid}"
    m2 = re.search(r"(https?://(?:m\.)?youtube\.com/shorts/([A-Za-z0-9_-]+))", url)
    if m2:
        vid = m2.group(2)
        return f"https://www.youtube.com/watch?v={vid}"
    m3 = re.search(r"(https?://youtube\.com/shorts/([A-Za-z0-9_-]+))", url)
    if m3:
        vid = m3.group(2)
        return f"https://www.youtube.com/watch?v={vid}"
    return url

def extract_first_url(text: str) -> str | None:
    if not text:
        return None
    found = re.findall(URL_RE, text)
    return found[0] if found else None

def is_terabox(url: str) -> bool:
    return any(host in url.lower() for host in [
        "terabox.com", "1024terabox.com", "teraboxapp.com"
    ])

def run_ytdlp(url: str, ua: str | None = None) -> str | None:
    # Download best format to a predictable temporary name pattern
    cmd = ["yt-dlp", "-f", "best", "-o", "yt_dlp_temp.%(ext)s", url]

    # If site needs special UA (Facebook commonly benefits from mobile UA)
    if ua:
        cmd += ["--user-agent", ua]

    # Helpful flags to reduce issues:
    # - Retry on transient network problems
    cmd += ["--retries", "3", "--fragment-retries", "3"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            for f in os.listdir():
                if f.startswith("yt_dlp_temp."):
                    return f
        else:
            print("yt-dlp stderr:", result.stderr)
    except Exception as e:
        print("yt-dlp exception:", e)
    return None

def upload_to_fileio(file_path: str) -> str | None:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post("https://file.io", files={"file": f}, timeout=180)
        if resp.ok:
            data = resp.json()
            if data.get("success"):
                return data.get("link")
            else:
                print("file.io response:", data)
        else:
            print("file.io status:", resp.status_code, resp.text[:200])
    except Exception as e:
        print("file.io error:", e)
    return None

def safe_edit(msg: Message, text: str, disable_preview: bool = False):
    try:
        return msg.edit(text, disable_web_page_preview=disable_preview)
    except MessageNotModified:
        return None

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    text = (
        "Hi! Send a file (up to 4GB) or a public link from YouTube, Instagram, Facebook, "
        "Twitter, or Terabox, and I’ll return a downloadable/playable link.\n\n"
        "- YouTube Shorts are auto-normalized; keep yt-dlp updated for best results.\n"
        "- Facebook/Instagram often require the post to be public.\n"
        "- Terabox direct links may require a specialized converter."
    )
    await message.reply(text)

@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file_upload(client, message: Message):
    media = message.document or message.video or message.audio
    if media and getattr(media, "file_size", 0) > 4 * 1024 * 1024 * 1024:
        await message.reply("❌ File exceeds 4GB limit on File.io.")
        return

    status = await message.reply("📥 Downloading your file from Telegram...")
    temp_name = "upload_temp_file"
    path = await client.download_media(message, file_name=temp_name)

    safe_edit(status, "📤 Uploading to File.io...")
    url = upload_to_fileio(path)

    # Clean up
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    if url:
        safe_edit(status, f"✅ Uploaded!\n📎 [Download / Play Now]({url})", disable_preview=False)
    else:
        safe_edit(status, "❌ Upload failed. Please try again.")

@app.on_message(filters.text & filters.private)
async def handle_link_text(client, message: Message):
    # Ignore bare commands like /start to avoid double replies
    if message.text and message.text.strip().startswith("/"):
        return

    url = extract_first_url(message.text)
    if not url:
        await message.reply("ℹ️ Send a file or a supported link (YouTube, Instagram, Facebook, Twitter, Terabox).")
        return

    # Normalize specific platforms
    url = normalize_url(url)

    status = await message.reply("🔎 Processing your link...")

    # Site-specific options
    ua = None
    if "facebook.com" in url.lower() or "fb.watch" in url.lower():
        # Mobile UA often helps with FB redirects/parsing
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1"

    if is_terabox(url):
        # Terabox is not reliably supported by yt-dlp; most cases need a converter service.
        safe_edit(status, "⚠️ Terabox direct links require a converter; not supported via yt-dlp. Try a public Terabox-to-direct API or send a different link.")
        return

    # Download via yt-dlp
    file_path = run_ytdlp(url, ua=ua)
    if not file_path:
        safe_edit(status, "❌ Could not download. Link may be private, region-locked, or unsupported. Ensure it's public and try again.")
        return

    safe_edit(status, "📤 Uploading to File.io...")
    final_url = upload_to_fileio(file_path)

    # Cleanup
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        # Remove any yt_dlp_temp leftovers
        for f in os.listdir():
            if f.startswith("yt_dlp_temp."):
                try:
                    os.remove(f)
                except Exception:
                    pass
    except Exception:
        pass

    if final_url:
        safe_edit(status, f"✅ Download Ready!\n▶️ [Click to Watch / Download]({final_url})", disable_preview=False)
    else:
        safe_edit(status, "❌ Upload failed after download. Please try again.")
