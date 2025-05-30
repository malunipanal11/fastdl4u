import os
import time
import asyncio
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes

def generate_code():
    return ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))

def cleanup_expired(app_state):
    now = time.time()
    to_delete = [k for k, v in app_state["shared_files"].items() if now > v["expiry"]]
    for code in to_delete:
        del app_state["shared_files"][code]

def start(app_state, admin_id):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        welcome_image_url = "https://i.postimg.cc/25v78k6g/FB-IMG-1746260578211.jpg"
        await update.message.reply_photo(welcome_image_url, caption="Hello baby, it's only for 18+ Only")
        await context.bot.send_chat_action(chat_id=user_id, action='typing')
        await asyncio.sleep(2)

        buttons = [
            [InlineKeyboardButton("/images", callback_data="images"),
             InlineKeyboardButton("/videos", callback_data="videos"),
             InlineKeyboardButton("/audio", callback_data="audio")]
        ]
        if user_id == admin_id:
            buttons.append([InlineKeyboardButton("/list", callback_data="admin_list")])
        else:
            buttons.append([InlineKeyboardButton("/list", callback_data="user_list")])
        await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(buttons))
    return inner

def handle_add(app_state, uploader, download_folder, admin_id):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id != admin_id:
            return

        file = update.message.document or update.message.video or (update.message.photo[-1] if update.message.photo else None)
        if not file:
            await update.message.reply_text("No media detected.")
            return

        file_name = getattr(file, "file_name", f"{file.file_unique_id}.jpg")
        file_path = os.path.join(download_folder, f"{file.file_unique_id}_{file_name}")

        new_file = await file.get_file()
        await new_file.download_to_drive(file_path)

        uploader.upload_to_platform(file_path, "Public")

        code = generate_code()
        expiry = time.time() + 24 * 3600
        app_state["shared_files"][code] = {
            "file": file_path,
            "expiry": expiry,
            "user": None
        }

        await update.message.reply_text(f"Saved with code: {code}\nAdd more or /done")
    return inner

def handle_list(app_state, admin_id):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        cleanup_expired(app_state)

        if user.id == admin_id:
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
    return inner

def handle_get(app_state):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        cleanup_expired(app_state)
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /get <code>")
            return

        code = args[0].upper()
        if code not in app_state["shared_files"]:
            await update.message.reply_text("Invalid or expired code.")
            return

        entry = app_state["shared_files"][code]
        file_path = entry["file"]
        await update.message.reply_document(InputFile(file_path))
    return inner

def handle_request(app_state):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /request <code>")
            return
        code = args[0].upper()
        user = update.effective_user
        app_state["requests"][code] = user.id
        await context.bot.send_message(chat_id=os.getenv("ADMIN_ID"), text=f"🚨 Request from @{user.username or user.id} for file {code}\nApprove? /approve {code} or /deny {code}")
        await update.message.reply_text("Request sent to admin.")
    return inner

def handle_approve(app_state):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            return
        code = args[0].upper()
        if code in app_state["requests"]:
            user_id = app_state["requests"].pop(code)
            app_state["shared_files"][code]["user"] = user_id
            await context.bot.send_message(chat_id=user_id, text=f"Approved. Use /get {code} to access the file (valid for 24 hrs)")
            await update.message.reply_text(f"Approved {code}.")
    return inner

def handle_deny(app_state):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            return
        code = args[0].upper()
        if code in app_state["requests"]:
            user_id = app_state["requests"].pop(code)
            await context.bot.send_message(chat_id=user_id, text="Your request was denied.")
            await update.message.reply_text(f"Denied {code}.")
    return inner
