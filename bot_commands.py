import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from drive_utils import upload_to_drive, list_files_in_folder, get_random_file

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Telegram bot application
app = Application.builder().token(TELEGRAM_TOKEN).build()

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /upload, /list or /random.")

# Command: /upload
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Create a file dynamically
        with open("telegram_upload.txt", "w") as f:
            f.write("Uploaded from /upload command!")

        file_id = upload_to_drive("telegram_upload.txt", "UploadedFromTelegram.txt", "BotFiles")
        await update.message.reply_text(f"Uploaded to Drive. File ID: {file_id}")
    except Exception as e:
        await update.message.reply_text(f"Upload failed: {str(e)}")

# Command: /list
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = list_files_in_folder("BotFiles")
        if not files:
            await update.message.reply_text("No files found.")
        else:
            file_list = "\n".join(f"{f['name']} ({f['id']})" for f in files)
            await update.message.reply_text(f"Files in Drive:\n{file_list}")
    except Exception as e:
        await update.message.reply_text(f"Listing failed: {str(e)}")

# Command: /random
async def random_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = get_random_file("BotFiles")
        if file:
            await update.message.reply_text(f"Random file: {file['name']} ({file['id']})")
        else:
            await update.message.reply_text("No files available.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Add command handlers to the bot
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("upload", upload))
app.add_handler(CommandHandler("list", list_files))
app.add_handler(CommandHandler("random", random_file))

# This function is called by FastAPI when a webhook update is received
async def handle_telegram_update(update_data: dict):
    update = Update.de_json(update_data, app.bot)
    await app.process_update(update)
