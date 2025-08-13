# --- Render Free Web Service PORT Fix (bind simple HTTP health) ---
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
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
import re, subprocess, requests, json, time

from config import API_ID, API_HASH, BOT_TOKEN

DATA_FILE = "data.json"

def load_db():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_messages": 0, "total_links_processed": 0, "total_files_processed": 0, "last_seen_user_ids": []}

def save_db(db):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("DB save error:", e)

db = load_db()

def bump_counter(field, user_id=None):
    db[field] = db.get(field, 0) + 1
    db["total_messages"] = db.get("total_messages", 0) + 1
    if user_id:
        ids = set(db.get("last_seen_user_ids", []))
        ids.add(user_id)
        db["last_seen_user_ids"] = list(ids)
    save_db(db)

def safe_edit(msg: Message, text: str, disable_preview: bool = False):
    try:
        return msg.edit(text, disable_web_page_preview=disable_preview)
    except MessageNotModified:
        return None
    except Exception as e:
        print("edit error:", e); return None

app = Client("multi_link_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

URL_RE = r"(https?://[^\s]+)"

def normalize_url(url: str) -> str:
    m = re.search(r"(?:https?://(?:www\.|m\.)?youtube\.com/shorts/)([A-Za-z0-9_-]+)", url)
    if m:
        vid = m.group(1)
        return f"https://www.youtube.com/watch?v={vid}"
    return url

def extract_first_url(text: str):
    if not text: return None
    found = re.findall(URL_RE, text)
    return found[0] if found else None

def is_terabox(url: str) -> bool:
    u = url.lower()
    return any(x in u for x in ["terabox.com", "1024terabox.com", "teraboxapp.com"])

def run_ytdlp(url: str, ua: str | None = None) -> str | None:
    cmd = ["yt-dlp", "-f", "best", "-o", "yt_dlp_temp.%(ext)s", url, "--retries", "3", "--fragment-retries", "3"]
    if ua:
        cmd += ["--user-agent", ua]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            for f in os.listdir():
                if f.startswith("yt_dlp_temp."):
                    return f
        else:
            print("yt-dlp stderr:", r.stderr[:400])
    except Exception as e:
        print("yt-dlp exception:", e)
    return None

def upload_to_fileio(file_path: str) -> str | None:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post("https://file.io", files={"file": f}, timeout=300)
        if resp.ok:
            data = resp.json()
            if data.get("success"):
                return data.get("link")
            print("file.io response:", data)
        else:
            print("file.io status:", resp.status_code, resp.text[:200])
    except Exception as e:
        print("file.io error:", e)
    return None

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    bump_counter("total_messages", message.from_user.id if message.from_user else None)
    txt = (
        "Hi! Send a file (≤4GB) or a public link from YouTube, Instagram, Facebook, "
        "Twitter, or Terabox and I’ll return a downloadable/playable link.\n\n"
        "Commands:\n"
        "/alive – show bot status and stats\n"
        "/start – help"
    )
    await message.reply(txt)

@app.on_message(filters.command("alive"))
async def alive_handler(client, message: Message):
    bump_counter("total_messages", message.from_user.id if message.from_user else None)
    users = len(db.get("last_seen_user_ids", []))
    txt = (
        "✅ Bot is alive.\n\n"
        f"Total messages: {db.get('total_messages', 0)}\n"
        f"Files processed: {db.get('total_files_processed', 0)}\n"
        f"Links processed: {db.get('total_links_processed', 0)}\n"
        f"Unique users: {users}\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC"
    )
    await message.reply(txt)

@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file_upload(client, message: Message):
    bump_counter("total_messages", message.from_user.id if message.from_user else None)
    media = message.document or message.video or message.audio
    if media and getattr(media, "file_size", 0) > 4 * 1024 * 1024 * 1024:
        await message.reply("❌ File exceeds 4GB File.io limit.")
        return

    status = await message.reply("📥 Downloading your file from Telegram...")
    path = await client.download_media(message, file_name="upload_temp_file")

    safe_edit(status, "📤 Uploading to File.io...")
    url = upload_to_fileio(path)

    try:
        if os.path.exists(path): os.remove(path)
    except Exception: pass

    if url:
        db["total_files_processed"] = db.get("total_files_processed", 0) + 1; save_db(db)
        safe_edit(status, f"✅ Uploaded!\n📎 [Download / Play Now]({url})", disable_preview=False)
    else:
        safe_edit(status, "❌ Upload failed. Please try again.")

@app.on_message(filters.text & filters.private)
async def handle_link_text(client, message: Message):
    # ignore commands like /start, /alive here
    if message.text and message.text.strip().startswith("/"):
        return

    bump_counter("total_messages", message.from_user.id if message.from_user else None)

    url = extract_first_url(message.text)
    if not url:
        await message.reply("ℹ️ Send a file or a supported link (YouTube, Instagram, Facebook, Twitter, Terabox).")
        return

    url = normalize_url(url)
    status = await message.reply("🔎 Processing your link...")

    ua = None
    if "facebook.com" in url.lower() or "fb.watch" in url.lower():
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1"

    if is_terabox(url):
        safe_edit(status, "⚠️ Terabox direct links need a converter (not via yt-dlp). Send a public video link or a file.")
        return

    file_path = run_ytdlp(url, ua=ua)
    if not file_path:
        safe_edit(status, "❌ Could not download. Ensure the link is public and try again.")
        return

    safe_edit(status, "📤 Uploading to File.io...")
    final_url = upload_to_fileio(file_path)

    try:
        if file_path and os.path.exists(file_path): os.remove(file_path)
        for f in os.listdir():
            if f.startswith("yt_dlp_temp."):
                try: os.remove(f)
                except Exception: pass
    except Exception: pass

    if final_url:
        db["total_links_processed"] = db.get("total_links_processed", 0) + 1; save_db(db)
        safe_edit(status, f"✅ Download Ready!\n▶️ [Click to Watch / Download]({final_url})", disable_preview=False)
    else:
        safe_edit(status, "❌ Upload failed after download. Please try again.")

app.run()
