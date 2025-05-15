import os
import logging
import tempfile
import shutil
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import Filters
from telegram.error import TelegramError
import re

from config import BOT_TOKEN, WELCOME_MESSAGE, HELP_MESSAGE
from downloader import download_media, is_valid_url, get_platform_name
from utils import cleanup_user_data, create_temp_dir, format_size

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define temp directory for downloads
TEMP_DIR = os.path.join(tempfile.gettempdir(), "fastdl4u_bot")

# Create temp directory if it doesn't exist
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Track user sessions and downloads
user_data = {}

def start_command(update: Update, context: CallbackContext):
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    
    # Try to import db and User model here to avoid circular imports
    try:
        from models import db, User
        from main import get_flask_app
        
        # Get the Flask app instance
        flask_app = get_flask_app()
        
        if flask_app:
            # Save user to database if they don't exist
            with flask_app.app_context():
                existing_user = User.query.filter_by(telegram_id=user.id).first()
                if not existing_user:
                    new_user = User(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    db.session.add(new_user)
                    db.session.commit()
                    logging.info(f"New user saved to database: {user.id}")
                else:
                    # Update user info if it has changed
                    if (existing_user.username != user.username or 
                        existing_user.first_name != user.first_name or 
                        existing_user.last_name != user.last_name):
                        existing_user.username = user.username
                        existing_user.first_name = user.first_name
                        existing_user.last_name = user.last_name
                        db.session.commit()
                        logging.info(f"Updated user info in database: {user.id}")
        else:
            logging.error("Flask app not available in global context")
    except Exception as e:
        logging.error(f"Error saving user to database: {str(e)}")
    
    update.message.reply_text(
        f"Hello, {user.first_name}!\n{WELCOME_MESSAGE}",
        parse_mode='Markdown'
    )

def help_command(update: Update, context: CallbackContext):
    """Send help message when the command /help is issued."""
    update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown'
    )

def cleanup_command(update: Update, context: CallbackContext):
    """Clean up user downloads and data when the command /cleanup is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_data:
        # Clean up user data
        cleanup_user_data(user_id, user_data, TEMP_DIR)
        update.message.reply_text("✅ All your previous downloads and message history have been cleaned up.")
    else:
        update.message.reply_text("No data to clean up.")

def handle_url(update: Update, context: CallbackContext):
    """Handle messages containing URLs."""
    message_text = update.message.text
    user_id = update.effective_user.id
    
    # Check if the message contains a URL
    if not is_valid_url(message_text):
        update.message.reply_text("Please send a valid URL from a supported platform.")
        return
    
    # Store the URL in user data
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['url'] = message_text
    platform = get_platform_name(message_text)
    
    # Send format selection buttons
    keyboard = [
        [
            InlineKeyboardButton("📹 Video", callback_data="format_video"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data="format_audio")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"I detected a {platform} link! Please choose a download format:",
        reply_markup=reply_markup
    )

def handle_callback(update: Update, context: CallbackContext):
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if user_id not in user_data or 'url' not in user_data[user_id]:
        query.edit_message_text("Session expired. Please send the URL again.")
        return
