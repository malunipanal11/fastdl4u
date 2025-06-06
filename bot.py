import os, logging, tempfile
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_DOMAIN")
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

app = FastAPI()
application: Application = Application.builder().token(TOKEN).build()

# ---- Downloader ----
async def download_video(url: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            filename = tmp_file.name

        ydl_opts = {
            'format': 'best',
            'outtmpl': filename,
            'quiet': True,
            'noplaylist': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0',
            }
        }

        with YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading {url}")
            ydl.download([url])

        return filename
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise

# ---- Upload to Gofile ----
async def upload_to_gofile(filepath: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            server_resp = await client.get("https://api.gofile.io/getServer")
            server = server_resp.json()["data"]["server"]

            with open(filepath, "rb") as f:
                files = {"file": (os.path.basename(filepath), f)}
                params = {"token": GOFILE_TOKEN}
                upload_url = f"https://{server}.gofile.io/uploadFile"
                resp = await client.post(upload_url, files=files, params=params)

        return resp.json()["data"]["downloadPage"]
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise

# ---- Commands ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send a video link (YouTube, Instagram, TikTok, etc.), and I'll give you a download link."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    await update.message.reply_text("⏳ Downloading...")

    try:
        file_path = await download_video(url)
        dl_url = await upload_to_gofile(file_path)
        await update.message.reply_text(f"✅ [Click to Download]({dl_url})", parse_mode="Markdown")
        os.remove(file_path)
    except Exception:
        await update.message.reply_text("❌ Failed to download video.")

# ---- Register Bot Handlers ----
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

# ---- FastAPI Webhook Setup ----
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.bot.set_my_commands([BotCommand("start", "Start the bot")])
    logging.info("✅ Webhook registered.")

@app.post("/")
async def telegram_webhook(req: Request):
    update = Update.de_json(await req.json(), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot is running"}
