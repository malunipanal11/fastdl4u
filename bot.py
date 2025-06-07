import os
import asyncio
import logging
import random
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from mega import Mega

logging.basicConfig(level=logging.INFO)

# Get from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split()]

# Global flags
upload_mode = {}
serial = {"img": 0, "vid": 0, "aud": 0}
mega = Mega().login(MEGA_EMAIL, MEGA_PASSWORD)


def get_serial(type_key):
    serial[type_key] += 1
    return f"{type_key}{serial[type_key]}"


async def delete_later(ctx: CallbackContext, chat_id: int, msg_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        ctx.bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


def is_admin(user_id):
    return user_id in ADMIN_IDS


# ───────────────────────────── Admin Commands ─────────────────────────────

def upload_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    if not is_admin(user.id):
        return
    upload_mode[user.id] = True
    msg = update.message.reply_text("✅ Upload mode ON. Send files.")
    context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, msg.chat.id, msg.message_id, 30)), 0)


def done_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id in upload_mode:
        upload_mode.pop(user.id)
    msg = update.message.reply_text("✅ Upload mode OFF.")
    context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, msg.chat.id, msg.message_id, 30)), 0)


def status_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot is alive.")


def info_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Mega Storage Bot\nSupports MEGA uploads, Telegram commands, and file organization.")


def link_cmd(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return

    args = context.args
    if not args or not args[0]:
        update.message.reply_text("Usage: /link img1 or /link vid2")
        return

    key = args[0]
    type_map = {"img": "IMAGES", "vid": "VIDEOS", "aud": "AUDIO"}
    prefix = key[:3]

    if prefix not in type_map:
        update.message.reply_text("❌ Invalid file ID.")
        return

    folder = mega.find(f"telegram_upload/{type_map[prefix]}")
    files = mega.get_files_in_node(folder)
    for f in files.values():
        if f['a']['n'] == key:
            link = mega.get_link(f)
            update.message.reply_text(f"🔗 Link for `{key}`:\n{link}")
            return

    update.message.reply_text("❌ File not found.")


# ───────────────────────────── File Handling ─────────────────────────────

def handle_upload(update: Update, context: CallbackContext):
    user = update.effective_user
    if not upload_mode.get(user.id):
        return

    file = update.message.document or update.message.video or update.message.audio or update.message.photo
    file_type = None
    file_obj = None

    if update.message.photo:
        file_type = "img"
        file_obj = update.message.photo[-1].get_file()
    elif update.message.video:
        file_type = "vid"
        file_obj = update.message.video.get_file()
    elif update.message.audio:
        file_type = "aud"
        file_obj = update.message.audio.get_file()
    elif update.message.document:
        mime = update.message.document.mime_type or ""
        if "image" in mime:
            file_type = "img"
        elif "video" in mime:
            file_type = "vid"
        elif "audio" in mime:
            file_type = "aud"
        file_obj = update.message.document.get_file()

    if not file_type or not file_obj:
        msg = update.message.reply_text("❌ Unsupported file type.")
        context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, msg.chat.id, msg.message_id, 30)), 0)
        return

    filename = get_serial(file_type)
    local_path = f"{filename}"
    file_obj.download(local_path)

    mega.upload(local_path, f"telegram_upload/{file_type.upper()}S/{filename}")
    os.remove(local_path)

    msg = update.message.reply_text(f"✅ Uploaded as `{filename}`")
    context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, msg.chat.id, msg.message_id, 30)), 0)
    context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, update.message.chat.id, update.message.message_id, 600)), 0)


# ───────────────────────────── Category Browsing ─────────────────────────────

def show_random(update: Update, context: CallbackContext):
    category = update.message.text.lower().replace("/", "").upper()
    folder = mega.find(f"telegram_upload/{category}")
    if not folder:
        update.message.reply_text("❌ Folder not found.")
        return

    files = mega.get_files_in_node(folder)
    if not files:
        update.message.reply_text("❌ No files available.")
        return

    chosen = random.choice(list(files.values()))
    link = mega.get_link(chosen)
    msg = update.message.reply_text(f"🎲 Random {category.title()}: {link}")
    context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_later(ctx, msg.chat.id, msg.message_id, 600)), 0)


# ───────────────────────────── Main ─────────────────────────────

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Admin
    dp.add_handler(CommandHandler("upload", upload_cmd))
    dp.add_handler(CommandHandler("done", done_cmd))
    dp.add_handler(CommandHandler("link", link_cmd, pass_args=True))
    dp.add_handler(CommandHandler("status", status_cmd))
    dp.add_handler(CommandHandler("info", info_cmd))

    # User
    dp.add_handler(CommandHandler("images", show_random))
    dp.add_handler(CommandHandler("videos", show_random))
    dp.add_handler(CommandHandler("audio", show_random))

    # Files
    dp.add_handler(MessageHandler(Filters.document | Filters.photo | Filters.video | Filters.audio, handle_upload))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
