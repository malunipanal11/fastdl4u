import os
import logging
import asyncio
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from mega import Mega
from threading import Timer

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))
STORAGE_FOLDER = "TelegramUploads"

# --- Setup ---
logging.basicConfig(level=logging.INFO)
mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

upload_mode = {}
file_counters = {"image": 0, "video": 0, "audio": 0}
file_db = {"image": [], "video": [], "audio": []}

# --- Core Commands ---

def is_admin(user_id):
    return user_id in ADMIN_IDS

def upload_to_mega(file_path, file_type):
    folder = f"{STORAGE_FOLDER}/{file_type}"
    try:
        m.find(folder)
    except:
        m.create_folder(folder)
    m.upload(file_path, m.find(folder)[0])
    os.remove(file_path)

def start_upload(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    upload_mode[update.effective_user.id] = True
    update.message.reply_text("Upload mode ON. Send files...")

def stop_upload(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    upload_mode[update.effective_user.id] = False
    update.message.reply_text("Upload mode OFF.")

def handle_file(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not upload_mode.get(user_id, False):
        return

    file = None
    file_type = None

    if update.message.photo:
        file = update.message.photo[-1].get_file()
        file_type = "image"
    elif update.message.video:
        file = update.message.video.get_file()
        file_type = "video"
    elif update.message.audio:
        file = update.message.audio.get_file()
        file_type = "audio"

    if not file_type:
        update.message.reply_text("Only images, videos, or audio allowed.")
        return

    file_counters[file_type] += 1
    serial = f"{file_type[:3]}{file_counters[file_type]}"
    filename = f"{serial}_{file.file_id}.bin"
    file_path = f"/tmp/{filename}"

    file.download(file_path)
    upload_to_mega(file_path, file_type)
    file_db[file_type].append((serial, file.file_id))

    sent_msg = update.message.reply_text(f"✅ Uploaded: {serial}")
    context.job_queue.run_once(lambda c: sent_msg.delete(), 30)

def get_random(update: Update, context: CallbackContext, cat):
    if not file_db[cat]:
        update.message.reply_text("❌ No files yet.")
        return
    import random
    serial, file_id = random.choice(file_db[cat])
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    msg = context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)
    context.job_queue.run_once(lambda c: msg.delete(), 600)

def show_image(update: Update, context: CallbackContext):
    get_random(update, context, "image")

def show_video(update: Update, context: CallbackContext):
    get_random(update, context, "video")

def show_audio(update: Update, context: CallbackContext):
    get_random(update, context, "audio")

def status(update: Update, context: CallbackContext):
    text = "\n".join(f"{k.capitalize()}s: {len(v)}" for k, v in file_db.items())
    update.message.reply_text(f"📊 Status:\n{text}")

def info(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Mega Upload Bot\nFiles auto-categorized & stored safely.")

def link(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        update.message.reply_text("Usage: /link <serial>")
        return
    for cat in file_db:
        for serial, file_id in file_db[cat]:
            if serial == args[0]:
                update.message.reply_text(f"Telegram file ID: `{file_id}`", parse_mode="Markdown")
                return
    update.message.reply_text("❌ Serial not found.")

# --- Main ---

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("upload", start_upload))
    dp.add_handler(CommandHandler("done", stop_upload))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("info", info))
    dp.add_handler(CommandHandler("link", link, pass_args=True))

    dp.add_handler(CommandHandler("images", show_image))
    dp.add_handler(CommandHandler("videos", show_video))
    dp.add_handler(CommandHandler("audio", show_audio))

    dp.add_handler(MessageHandler(Filters.document | Filters.photo | Filters.video | Filters.audio, handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
