import os
import logging
import tempfile
import shutil
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import filters
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
    
    url = user_data[user_id]['url']
    
    if callback_data.startswith("format_"):
        format_type = callback_data.split("_")[1]
        user_data[user_id]['format'] = format_type
        
        # Create user temp directory
        user_temp_dir = create_temp_dir(user_id, TEMP_DIR)
        
        # Send download status message
        status_message = query.edit_message_text("⏳ Downloading... Please wait, this may take a while.")
        
        # Record download in database
        download_record = None
        platform = get_platform_name(url)
        
        try:
            # Try to import db and models here to avoid circular imports
            from models import db, User, Download
            from main import get_flask_app
            
            # Get the Flask app instance
            flask_app = get_flask_app()
            
            if flask_app:
                with flask_app.app_context():
                    # Get the database user
                    db_user = User.query.filter_by(telegram_id=user_id).first()
                    if not db_user:
                        # Create the user if they don't exist
                        tg_user = update.effective_user
                        db_user = User(
                            telegram_id=user_id,
                            username=tg_user.username,
                            first_name=tg_user.first_name,
                            last_name=tg_user.last_name
                        )
                        db.session.add(db_user)
                        db.session.commit()
                        logging.info(f"New user created during download: {user_id}")
                    
                    # Create download record
                    download_record = Download(
                        user_id=db_user.id,
                        url=url,
                        platform=platform,
                        format_type=format_type,
                        status='started'
                    )
                    db.session.add(download_record)
                    db.session.commit()
                    logging.info(f"Download record created: {url} for user {user_id}")
            else:
                logging.error("Flask app not available in global context for download record")
        except Exception as e:
            logger.error(f"Error recording download in database: {str(e)}")
        
        download_start_time = time.time()
        
        try:
            # Create a new asyncio event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            # Download the media in the new loop
            download_info = new_loop.run_until_complete(download_media(url, format_type, user_temp_dir))
            download_time = time.time() - download_start_time
            
            if download_info and 'file_path' in download_info:
                file_path = download_info['file_path']
                title = download_info.get('title', 'Downloaded Media')
                
                # Format file size
                file_size = os.path.getsize(file_path)
                formatted_size = format_size(file_size)
                
                # Update status message
                status_message.edit_text(f"✅ Download complete!\n\nTitle: {title}\nSize: {formatted_size}\n\n⏳ Uploading to Telegram...")
                
                # Upload to Telegram
                if format_type == 'video':
                    with open(file_path, 'rb') as video_file:
                        context.bot.send_video(
                            chat_id=user_id,
                            video=video_file,
                            caption=f"📹 {title}",
                            supports_streaming=True,
                            filename=os.path.basename(file_path)
                        )
                else:  # audio
                    with open(file_path, 'rb') as audio_file:
                        context.bot.send_audio(
                            chat_id=user_id,
                            audio=audio_file,
                            caption=f"🎵 {title}",
                            filename=os.path.basename(file_path)
                        )
                
                # Update final status
                status_message.edit_text(f"✅ Download and upload complete!\n\nTitle: {title}\nSize: {formatted_size}")
                
                # Update download record in database
                try:
                    from models import db, Download
                    from main import get_flask_app
                    
                    # Get the Flask app instance
                    flask_app = get_flask_app()
                    
                    if flask_app:
                        with flask_app.app_context():
                            if download_record:
                                download_record = Download.query.get(download_record.id)
                                if download_record:
                                    download_record.status = 'completed'
                                    download_record.title = title
                                    download_record.file_size = file_size
                                    download_record.download_time = download_time
                                    db.session.commit()
                                    logging.info(f"Updated download record as completed: {download_record.id}")
                    else:
                        logging.error("Flask app not available in global context for updating download record")
                except Exception as e:
                    logger.error(f"Error updating download record: {str(e)}")
                
            else:
                error_message = download_info.get('error', 'Unknown error occurred during download.')
                status_message.edit_text(f"❌ Download failed: {error_message}")
                
                # Update download record in database for failed download
                try:
                    from models import db, Download
                    import builtins
                    
                    # Use the globally stored Flask app from builtins
                    flask_app = getattr(builtins, 'flask_app', None)
                    
                    if flask_app:
                        with flask_app.app_context():
                            if download_record:
                                download_record = Download.query.get(download_record.id)
                                if download_record:
                                    download_record.status = 'failed'
                                    download_record.error_message = error_message
                                    download_record.download_time = download_time
                                    db.session.commit()
                                    logging.info(f"Updated download record as failed: {download_record.id}")
                    else:
                        logging.error("Flask app not available in global context for updating failed download record")
                except Exception as e:
                    logger.error(f"Error updating failed download record: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during download/upload: {str(e)}")
            status_message.edit_text(f"❌ Error during download or upload: {str(e)}")
            
            # Update download record in database for error
            try:
                from models import db, Download
                import builtins
                
                # Use the globally stored Flask app from builtins
                flask_app = getattr(builtins, 'flask_app', None)
                
                if flask_app:
                    with flask_app.app_context():
                        if download_record:
                            download_record = Download.query.get(download_record.id)
                            if download_record:
                                download_record.status = 'failed'
                                download_record.error_message = str(e)
                                download_record.download_time = time.time() - download_start_time
                                db.session.commit()
                                logging.info(f"Updated download record after error: {download_record.id}")
                else:
                    logging.error("Flask app not available in global context for updating error download record")
            except Exception as db_error:
                logger.error(f"Error updating error download record: {str(db_error)}")
            
        finally:
            # Clean up after sending
            if user_id in user_data:
                cleanup_user_data(user_id, user_data, TEMP_DIR)

def handle_message(update: Update, context: CallbackContext):
    """Handle non-URL messages."""
    message_text = update.message.text
    
    # Check if the message contains a URL
    url_pattern = re.compile(r'https?://\S+')
    if url_pattern.search(message_text):
        handle_url(update, context)
    else:
        update.message.reply_text("Please send a valid URL from a supported platform (YouTube, Instagram, TikTok, etc.)")

def run():
    """Run the bot."""
    try:
        # Create updater
        updater = Updater(token=BOT_TOKEN)
        dispatcher = updater.dispatcher
        
        # Add handlers
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("cleanup", cleanup_command))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dispatcher.add_handler(CallbackQueryHandler(handle_callback))
        
        # Start the Bot
        updater.start_polling()
        return True
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        return False

# Create bot instance with run method
class Bot:
    @staticmethod
    def run():
        return run()
