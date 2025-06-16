import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from drive_utils import upload_to_drive, get_random_file

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable")

# Initializes the bot application (not run in polling mode)
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I’m your Google Drive bot. Use /upload or /random.")

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        await update.message.reply_text("📄 Please send a file to upload.")
        return

    file = update.message.document
    file_path = f"/tmp/{file.file_name}"

    # Download the file
    file_obj = await file.get_file()
    await file_obj.download_to_drive(file_path)

    # Upload to Google Drive
    file_id = upload_to_drive(file_path, file.file_name, "BotFiles")
    await update.message.reply_text(f"✅ Uploaded `{file.file_name}` to Drive.\nID: `{file_id}`", parse_mode="Markdown")

async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = get_random_file("BotFiles")
    if file:
        await update.message.reply_text(f"🎲 Random File: {file['name']} (ID: `{file['id']}`)", parse_mode="Markdown")
    else:
        await update.message.reply_text("📂 No files found in Drive folder.")

# Add handlers to the app
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("random", random))
app.add_handler(CommandHandler("upload", upload))  # In practice, upload is triggered by document

# --- Function to process updates from webhook ---
async def handle_telegram_update(update_data):
    update = Update.de_json(update_data, app.bot)
    await app.process_update(update)
