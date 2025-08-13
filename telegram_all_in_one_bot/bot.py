from pyrogram import Client, filters
from pyrogram.types import Message
import os
import re
import subprocess
import requests

from config import API_ID, API_HASH, BOT_TOKEN

# Create bot client
app = Client(
    "multi_link_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Regex to detect links
url_pattern = r"(https?://[^\s]+)"

# Check if message has a supported URL
def contains_supported_url(text: str):
    if text:
        urls = re.findall(url_pattern, text)
        if urls:
            return urls[0]  # first URL found
    return None

# Download from URL using yt-dlp
def download_with_ytdlp(url: str):
    try:
        filename = "yt_dlp_temp.%(ext)s"
        result = subprocess.run(
            ["yt-dlp", "-f", "best", "-o", filename, url],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            # Find the downloaded file's exact name
            for f in os.listdir():
                if f.startswith("yt_dlp_temp"):
                    return f
        else:
            print("yt-dlp error:", result.stderr)
        return None
    except Exception as e:
        print("Download error:", e)
        return None

# Upload file to File.io
def upload_to_fileio(file_path):
    with open(file_path, 'rb') as f:
        resp = requests.post("https://file.io", files={"file": f})
    if resp.ok and resp.json().get("success"):
        return resp.json().get("link")
    return None

# Handle direct Telegram file uploads
@app.on_message(filters.document | filters.video | filters.audio)
async def handle_file_upload(client, message: Message):
    file = message.document or message.video or message.audio
    if file.file_size > 4 * 1024 * 1024 * 1024:
        await message.reply("❌ File exceeds 4GB limit for File.io")
        return

    status = await message.reply("📥 Downloading your file from Telegram...")
    path = await client.download_media(message, file_name="upload_temp_file")

    await status.edit("📤 Uploading to File.io...")
    url = upload_to_fileio(path)
    os.remove(path)

    if url:
        await status.edit(f"✅ Uploaded!\n📎 [Download / Play Now]({url})", disable_web_page_preview=False)
    else:
        await status.edit("❌ Upload failed. Please try again.")

# Handle links from supported sites
@app.on_message(filters.text & filters.private)
async def handle_links(client, message: Message):
    url = contains_supported_url(message.text)
    if not url:
        return await message.reply(
            "ℹ️ Send me a **file** or a **link** from YouTube, Instagram, Facebook, Twitter, or Terabox."
        )

    status = await message.reply("🔎 Processing your link...")

    file_path = download_with_ytdlp(url)
    if not file_path:
        return await status.edit("❌ Couldn't download. Link may be private or unsupported.")

    await status.edit("📤 Uploading to File.io...")
    upload_url = upload_to_fileio(file_path)
    os.remove(file_path)

    if upload_url:
        await status.edit(f"✅ Download Ready!\n▶️ [Click to Watch / Download]({upload_url})", disable_web_page_preview=False)
    else:
        await status.edit("❌ Upload failed after download. Try again.")

# Start the bot
app.run()
