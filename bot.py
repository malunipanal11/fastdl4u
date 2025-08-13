# --- Render Free Web Service PORT Fix ---
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_server():
    port = int(os.environ.get("PORT", "10000"))  # Render uses $PORT
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Start the HTTP health server in background thread
threading.Thread(target=start_health_server, daemon=True).start()
# ---------------------------------------------

from pyrogram import Client, filters
from pyrogram.types import Message
import re
import subprocess
import requests
import os
from config import API_ID, API_HASH, BOT_TOKEN
from pyrogram.errors import MessageNotModified

# Telegram bot client
app = Client(
    "multi_link_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# URL regex pattern
url_pattern = r"(https?://[^\s]+)"

def contains_supported_url(text: str):
    if text:
        urls = re.findall(url_pattern, text)
        if urls:
            return urls[0]
    return None

# Download media via yt-dlp
def download_with_ytdlp(url: str):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "best", "-o", "yt_dlp_temp.%(ext)s", url],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for f in os.listdir():
                if f.startswith("yt_dlp_temp"):
                    return f
        else:
            print("yt-dlp error:", result.stderr)
        return None
    except Exception as e:
        print("Download error:", e)
        return None

# Upload any file to File.io
def upload_to_fileio(file_path):
    try:
        with open(file_path, 'rb') as f:
            resp = requests.post("https://file.io", files={"file": f})
        if resp.ok and resp.json().get("success"):
            return resp.json().get("link")
    except Exception as e:
        print("File.io upload error:", e)
    return None

@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file_upload(client, message: Message):
    file = message.document or message.video or message.audio
    if file.file_size > 4 * 1024 * 1024 * 1024:
        await message.reply("❌ File exceeds 4 GB limit on File.io.")
        return

    status = await message.reply("📥 Downloading your file from Telegram...")
    path = await client.download_media(message, file_name="upload_temp_file")

    try:
        await status.edit("📤 Uploading to File.io...")
    except MessageNotModified:
        pass

    url = upload_to_fileio(path)
    os.remove(path)

    if url:
        try:
            await status.edit(f"✅ Uploaded!\n📎 [Download / Play Now]({url})",
                              disable_web_page_preview=False)
        except MessageNotModified:
            pass
    else:
        try:
            await status.edit("❌ Upload failed.")
        except MessageNotModified:
            pass

@app.on_message(filters.text & filters.private)
async def handle_links(client, message: Message):
    url = contains_supported_url(message.text)
    if not url:
        await message.reply("ℹ️ Send a file or a supported link (YouTube, Instagram, Facebook, Twitter, Terabox).")
        return

    status = await message.reply("🔎 Processing your link...")

    file_path = download_with_ytdlp(url)
    if not file_path:
        try:
            await status.edit("❌ Could not download. Link may be private or unsupported.")
        except MessageNotModified:
            pass
        return

    try:
        await status.edit("📤 Uploading to File.io...")
    except MessageNotModified:
        pass

    upload_url = upload_to_fileio(file_path)
    os.remove(file_path)

    if upload_url:
        try:
            await status.edit(f"✅ Download Ready!\n▶️ [Click to Watch / Download]({upload_url})",
                              disable_web_page_preview=False)
        except MessageNotModified:
            pass
    else:
        try:
            await status.edit("❌ Upload failed after download.")
        except MessageNotModified:
            pass

# Start the bot
app.run()
