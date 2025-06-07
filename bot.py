import os
import asyncio
import random
from dotenv import load_dotenv
from mega import Mega
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

UPLOAD_FOLDER = "TelegramUploads"
CATEGORIES = {"Images": "img", "Video": "vid", "Audio": "aud"}

session_files = {}
serial_counter = {"img": 0, "vid": 0, "aud": 0}
user_uploading = set()

async def delete_later(context, message, delay=30):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except:
        pass

async def delete_local_file_later(path, delay=600):
    await asyncio.sleep(delay)
    if os.path.exists(path):
        os.remove(path)

def categorize(mime_type):
    if mime_type.startswith("image"):
        return "Images", "img"
    if mime_type.startswith("video"):
        return "Video", "vid"
    if mime_type.startswith("audio"):
        return "Audio", "aud"
    return "Documents", "doc"

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_uploading.add(update.effective_user.id)
    msg = await update.message.reply_text("Upload mode activated.")
    await delete_later(context, msg)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_uploading.discard(update.effective_user.id)
    count = len(session_files.get(update.effective_user.id, []))
    msg = await update.message.reply_text(f"Upload mode exited. {count} files uploaded.")
    session_files[update.effective_user.id] = []
    await delete_later(context, msg)

async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in user_uploading:
        return

    file = update.message.document or update.message.photo[-1] or update.message.video or update.message.audio
    if not file:
        return

    file_id = file.file_id
    file_obj = await context.bot.get_file(file_id)
    file_name = file.file_name if hasattr(file, 'file_name') and file.file_name else f"{file_id}.bin"
    local_path = f"./downloads/{file_name}"
    os.makedirs("./downloads", exist_ok=True)

    await file_obj.download_to_drive(local_path)

    mime_type = file.mime_type if hasattr(file, 'mime_type') else "application/octet-stream"
    category_name, prefix = categorize(mime_type)
    serial_counter[prefix] += 1
    serial = f"{prefix}{serial_counter[prefix]}"

    mega_folder = m.find(UPLOAD_FOLDER)
    if not mega_folder:
        mega_folder = m.create_folder(UPLOAD_FOLDER)
    subfolder = m.find(f"{UPLOAD_FOLDER}/{category_name}")
    if not subfolder:
        subfolder = m.create_folder(category_name, parent=mega_folder[0])

    uploaded = m.upload(local_path, subfolder[0])
    link = m.get_upload_link(uploaded)

    user_id = update.effective_user.id
    if user_id not in session_files:
        session_files[user_id] = []
    session_files[user_id].append({"serial": serial, "name": file_name, "link": link})

    msg = await update.message.reply_text(
        f"✅ Upload successful!\n🔢 ID: {serial}\n📁 Category: {category_name}\n🔗 [Link]({link})",
        disable_web_page_preview=True
    )
    await delete_later(context, msg)
    asyncio.create_task(delete_local_file_later(local_path))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    files = session_files.get(update.effective_user.id, [])
    if not files:
        msg = await update.message.reply_text("No files uploaded this session.")
    else:
        msg = await update.message.reply_text(
            "🗂 Uploaded Files:\n" +
            "\n".join([f"{f['serial']} - {f['name']}" for f in files])
        )
    await delete_later(context, msg)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    info = m.get_quota()
    msg = await update.message.reply_text(
        f"📦 MEGA Storage Used: {info['used'] / 1e9:.2f} GB / {info['total'] / 1e9:.2f} GB"
    )
    await delete_later(context, msg)

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return
    target_serial = context.args[0].strip()
    files = session_files.get(update.effective_user.id, [])
    for f in files:
        if f['serial'] == target_serial:
            msg = await update.message.reply_text(f"{f['serial']} - {f['name']}\n🔗 {f['link']}")
            await delete_later(context, msg)
            return
    msg = await update.message.reply_text("❌ Serial not found.")
    await delete_later(context, msg)

async def random_file(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: str):
    mega_folder = m.find(f"{UPLOAD_FOLDER}/{cat}")
    if not mega_folder:
        msg = await update.message.reply_text(f"No files found in {cat}.")
        await delete_later(context, msg)
        return
    files = m.get_files_in_node(mega_folder[0])
    if not files:
        msg = await update.message.reply_text(f"No files found in {cat}.")
        await delete_later(context, msg)
        return
    chosen = random.choice(files)
    name = chosen['name']
    link = m.get_link(chosen)
    prefix = CATEGORIES[cat]
    msg = await update.message.reply_text(
        f"🎲 Random {cat[:-1]}:\n📄 {name}\n🔗 {link}",
        disable_web_page_preview=True
    )
    await delete_later(context, msg)

async def images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await random_file(update, context, "Images")

async def videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await random_file(update, context, "Video")

async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await random_file(update, context, "Audio")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("upload", start_upload))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CommandHandler("images", images))
    app.add_handler(CommandHandler("videos", videos))
    app.add_handler(CommandHandler("audio", audio))
    app.add_handler(MessageHandler(filters.ALL, upload_handler))
    app.run_polling()
