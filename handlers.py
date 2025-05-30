import os
import time
import random
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes
from bot.mega_utils import MegaStorage

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

mega = MegaStorage()
app_state = {
    "requests": {},
    "shared_files": {},
}

def generate_code():
    return ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))

def cleanup_expired():
    now = time.time()
    to_delete = [k for k, v in app_state["shared_files"].items() if now > v["expiry"]]
    for code in to_delete:
        del app_state["shared_files"][code]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    welcome_url = "https://i.postimg.cc/25v78k6g/FB-IMG-1746260578211.jpg"
    await update.message.reply_photo(welcome_url, caption="Hello baby, it's only for 18+ Only")
    await asyncio.sleep(30)

    buttons = [
        [InlineKeyboardButton("/images", callback_data="images"),
         InlineKeyboardButton("/videos", callback_data="videos"),
         InlineKeyboardButton("/audio", callback_data="audio")]
    ]
    if user_id == int(os.getenv("ADMIN_ID")):
        buttons.append([InlineKeyboardButton("/list", callback_data="admin_list")])
    else:
        buttons.append([InlineKeyboardButton("/list", callback_data="user_list")])
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != int(os.getenv("ADMIN_ID")):
        return

    file = update.message.document or update.message.video or update.message.photo[-1] if update.message.photo else None
    if not file:
        await update.message.reply_text("No media detected.")
        return

    file_path = os.path.join(DOWNLOAD_FOLDER, f"{file.file_unique_id}_{file.file_name}")
    new_file = await file.get_file()
    await new_file.download_to_drive(file_path)

    mega.upload_file(file_path)

    code = generate_code()
    expiry = time.time() + 24 * 3600
    app_state["shared_files"][code] = {"file": file_path, "expiry": expiry, "user": None}
    await update.message.reply_text(f"Saved with code: {code}\nAdd more or /done")

async def handle_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cleanup_expired()
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /get <code>")
        return
    code = args[0].upper()
    entry = app_state["shared_files"].get(code)
    if not entry:
        await update.message.reply_text("Invalid or expired code.")
        return
    await update.message.reply_document(InputFile(entry["file"]))

async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cleanup_expired()
    if user.id == int(os.getenv("ADMIN_ID")):
        text = "📁 Your Files:\n"
        for code, data in app_state["shared_files"].items():
            name = os.path.basename(data["file"])
            text += f"{code} - {name}\n"
        await update.message.reply_text(text)
    else:
        text = "📁 Public Files (Request required):\n"
        for code, data in app_state["shared_files"].items():
            name = os.path.basename(data["file"])
            text += f"{name} - /request {code}\n"
        await update.message.reply_text(text)

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /request <code>")
        return
    code = args[0].upper()
    user = update.effective_user
    app_state["requests"][code] = user.id
    await context.bot.send_message(
        chat_id=int(os.getenv("ADMIN_ID")),
        text=f"🔔 Request from @{user.username} for file {code}\nApprove? /approve {code} or /deny {code}"
    )
    await update.message.reply_text("Request sent to admin.")

async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        return
    code = args[0].upper()
    if code in app_state["requests"]:
        user_id = app_state["requests"].pop(code)
        app_state["shared_files"][code]["user"] = user_id
        await context.bot.send_message(chat_id=user_id, text=f"Approved. Use /get {code} (valid 24 hrs)")
        await update.message.reply_text(f"Approved {code}.")

async def handle_deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        return
    code = args[0].upper()
    if code in app_state["requests"]:
        user_id = app_state["requests"].pop(code)
        await context.bot.send_message(chat_id=user_id, text="❌ Request denied.")
        await update.message.reply_text(f"Denied {code}.")
