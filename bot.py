import os import json import logging import random from fastapi import FastAPI, Request from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters from typing import Dict, List import httpx

TOKEN = os.getenv("BOT_TOKEN") WEBHOOK_URL = os.getenv("WEBHOOK_DOMAIN") + "/webhook" GOFILE_TOKEN = os.getenv("GOFILE_TOKEN") ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

logging.basicConfig(level=logging.INFO) logger = logging.getLogger("bot")

app = FastAPI() application: Application = Application.builder().token(TOKEN).build()

user_states: Dict[int, bool] = {} user_uploads: Dict[int, List[Dict[str, str]]] = {}

type_map = { "images": "img", "videos": "video", "audios": "audio", "files": "file", "texts": "text" }

async def upload_to_gofile(file_bytes: bytes, filename: str) -> str: async with httpx.AsyncClient() as client: response = await client.get("https://api.gofile.io/getServer") server = response.json()["data"]["server"] files = {"file": (filename, file_bytes)} params = {"token": GOFILE_TOKEN} upload_resp = await client.post( f"https://{server}.gofile.io/uploadFile", files=files, params=params ) data = upload_resp.json() if data["status"] != "ok": raise Exception(f"Gofile upload failed: {data}") logger.info(f"Gofile upload response: {data}") return data["data"]["downloadPage"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("✅ Bot is alive and ready!")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if user_id not in ADMIN_IDS: await update.message.reply_text("❌ You are not allowed to upload files.") return user_states[user_id] = True user_uploads.setdefault(user_id, []) await update.message.reply_text("✅ Upload mode ON. Send files or text.\nWhen done, send /done.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id user_states[user_id] = False await update.message.reply_text("✅ Upload mode OFF.")

async def send_random_from_category(update: Update, context: ContextTypes.DEFAULT_TYPE): category = update.message.text[1:].lower() user_id = update.effective_user.id all_items = [f for uploads in user_uploads.values() for f in uploads if f["type"] == category]

if not all_items:
    await update.message.reply_text(f"❌ No {category} uploaded yet.")
    return

file = random.choice(all_items)
keyboard = [[
    InlineKeyboardButton("▶️ Play", url=file["url"]),
    InlineKeyboardButton("⬇️ Download", url=file["url"])
]]
if user_id in ADMIN_IDS:
    keyboard[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{file['url']}"))
    keyboard[0].append(InlineKeyboardButton("📤 Send", callback_data=f"send:{file['url']}"))
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(f"📂 Random {category}:", reply_markup=reply_markup)

async def get_by_serial(update: Update, context: ContextTypes.DEFAULT_TYPE): if not context.args: await update.message.reply_text("❌ Usage: /get <serial> (e.g., img1, video2)") return

serial = context.args[0].lower()
for full_type, short in type_map.items():
    if serial.startswith(short):
        try:
            index = int(serial[len(short):]) - 1
        except ValueError:
            continue
        all_items = [f for uploads in user_uploads.values() for f in uploads if f["type"] == full_type]
        if index >= len(all_items):
            await update.message.reply_text("❌ File not found.")
            return
        file = all_items[index]
        user_id = update.effective_user.id
        keyboard = [[
            InlineKeyboardButton("▶️ Play", url=file["url"]),
            InlineKeyboardButton("⬇️ Download", url=file["url"])
        ]]
        if user_id in ADMIN_IDS:
            keyboard[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{file['url']}"))
            keyboard[0].append(InlineKeyboardButton("📤 Send", callback_data=f"send:{file['url']}"))
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"📦 Here is `{serial}`:", reply_markup=reply_markup, parse_mode="Markdown")
        return
await update.message.reply_text("❌ Invalid serial format.")

async def list_uploads(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id items = user_uploads.get(user_id, []) if not items: await update.message.reply_text("❌ No files uploaded.") return msg = "📦 Your uploads:\n" for item in items: msg += f"- {item['serial']} ({item['type']})\n" await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() data = query.data

if data.startswith("delete:"):
    url = data.split(":", 1)[1]
    for uploads in user_uploads.values():
        for i, item in enumerate(uploads):
            if item["url"] == url:
                del uploads[i]
                await query.edit_message_text("🗑️ File deleted.")
                return
    await query.edit_message_text("❌ File not found.")

elif data.startswith("send:"):
    url = data.split(":", 1)[1]
    await query.message.reply_text(f"📤 File URL: {url}")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE): if not update.message: return

user_id = update.effective_user.id
logger.info(f"Received message from {user_id}: {update.message}")

if user_id not in ADMIN_IDS or not user_states.get(user_id, False):
    logger.info("Upload skipped: Not in upload mode or not admin.")
    return

file_type, tg_file, filename = None, None, "file"

if update.message.photo:
    tg_file = await update.message.photo[-1].get_file()
    file_type = "images"
    filename += ".jpg"
elif update.message.document:
    tg_file = await update.message.document.get_file()
    file_type = "files"
    filename = update.message.document.file_name
elif update.message.video:
    tg_file = await update.message.video.get_file()
    file_type = "videos"
    filename = update.message.video.file_name or "video.mp4"
elif update.message.audio:
    tg_file = await update.message.audio.get_file()
    file_type = "audios"
    filename = update.message.audio.file_name or "audio.mp3"
elif update.message.text and not any([update.message.photo, update.message.video, update.message.audio, update.message.document]):
    content = update.message.text.encode()
    url = await upload_to_gofile(content, "text.txt")
    user_uploads.setdefault(user_id, [])
    count = sum(1 for f in user_uploads[user_id] if f["type"] == "texts")
    serial_number = f"text{count + 1}"
    user_uploads[user_id].append({"type": "texts", "url": url, "serial": serial_number})
    logger.info(f"Uploaded {serial_number} to {url}")
    await update.message.reply_text(f"✅ Received `{serial_number}`", parse_mode="Markdown")
    return

if tg_file:
    file_bytes = await tg_file.download_as_bytearray()
    url = await upload_to_gofile(file_bytes, filename)
    user_uploads.setdefault(user_id, [])
    count = sum(1 for f in user_uploads[user_id] if f["type"] == file_type)
    serial_number = f"{type_map[file_type]}{count + 1}"
    user_uploads[user_id].append({"type": file_type, "url": url, "serial": serial_number})
    logger.info(f"Uploaded {serial_number} to {url}")
    await update.message.reply_text(f"✅ Received `{serial_number}`", parse_mode="Markdown")

application.add_handler(CommandHandler("start", start)) application.add_handler(CommandHandler("add", add)) application.add_handler(CommandHandler("done", done)) application.add_handler(CommandHandler("images", send_random_from_category)) application.add_handler(CommandHandler("videos", send_random_from_category)) application.add_handler(CommandHandler("audios", send_random_from_category)) application.add_handler(CommandHandler("files", send_random_from_category)) application.add_handler(CommandHandler("texts", send_random_from_category)) application.add_handler(CommandHandler("get", get_by_serial)) application.add_handler(CommandHandler("list", list_uploads)) application.add_handler(CallbackQueryHandler(handle_callback)) application.add_handler(MessageHandler(filters.ALL, handle_file))

@app.on_event("startup") async def startup_event(): await application.initialize() await application.bot.set_webhook(f"{WEBHOOK_URL}") commands = [ BotCommand("start", "Start the bot"), BotCommand("images", "Random image"), BotCommand("videos", "Random video"), BotCommand("audios", "Random audio"), BotCommand("files", "Random file"), BotCommand("texts", "Random text"), BotCommand("get", "Get by serial"), BotCommand("list", "List your uploads") ] if ADMIN_IDS: commands += [ BotCommand("add", "Enter upload mode"), BotCommand("done", "Exit upload mode") ] await application.bot.set_my_commands(commands) logger.info("✅ Webhook and commands registered.") await application.start()

@app.post("/webhook") async def telegram_webhook(req: Request): body = await req.body() update_dict = json.loads(body) update = Update.de_json(update_dict, bot=application.bot) await application.process_update(update) return {"status": "ok"}

@app.get("/") async def root(): return {"message": "Bot is running."}

