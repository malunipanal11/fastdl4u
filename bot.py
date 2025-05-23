import os
import json
import time
import requests
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import yt_dlp

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables. Set it in .env file or environment.")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Media Downloader Bot! 🎬\n\n"
        "Send me a link from YouTube, Instagram, Facebook, or other supported platforms, "
        "and I'll help you download it as video or audio.\n\n"
        "Type /help for more information."
    )


# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(
        "📱 *Media Downloader Bot Help* 📱\n\n"
        "*Features:*\n"
        "• Download videos/audios from YouTube, Facebook, Instagram, and many other platforms\n"
        "• Get video thumbnail, platform info, and duration\n"
        "• Choose between Ultra HD Video or MP3 Audio\n"
        "• Files are hosted via GoFile for easy access\n\n"
        "*Commands:*\n"
        "• Send any video link to start downloading\n"
        "• /list - View your last 10 downloads\n"
        "• /cleanup - Clear your download history\n"
        "• /help - Show this help message\n\n"
        "Just paste a link to get started!",
        parse_mode="Markdown"
    )


# Handle user link
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the user message containing a link."""
    url = update.message.text.strip()
    
    # Check if user has reached the download limit
    if len(context.user_data.get('downloads', [])) >= 10:
        await update.message.reply_text(
            "❗ You've reached the maximum download limit (10 items).\n"
            "Use /cleanup to clear your history or remove individual downloads using /list."
        )
        return
    
    # Send a "processing" message
    processing_msg = await update.message.reply_text("🔎 Analyzing link, please wait...")
    
    try:
        # Extract information without downloading
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Extract metadata
        title = info.get("title", "Unknown Title")
        duration_seconds = info.get("duration", 0)
        duration = info.get("duration_string") or f"{duration_seconds} sec" if duration_seconds else "Unknown"
        thumbnail = info.get("thumbnail")
        webpage_url = info.get("webpage_url", url)
        platform = info.get("extractor_key", "Unknown").replace('IE', '')
        
        # Store metadata in user context
        context.user_data['meta'] = {
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "platform": platform,
            "source_url": webpage_url
        }
        
        # Create buttons for download options
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ultra HD Video 🎬", callback_data=f"video|{url}")],
            [InlineKeyboardButton("MP3 Audio 🎵", callback_data=f"audio|{url}")],
            [InlineKeyboardButton("Cancel ❌", callback_data="cancel")]
        ])
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send video info with download options
        await update.message.reply_photo(
            photo=thumbnail,
            caption=f"*{title}*\n\n📺 Platform: {platform}\n⏱ Duration: {duration}",
            parse_mode="Markdown",
            reply_markup=buttons
        )
        
    except Exception as e:
        logger.error(f"Error extracting info: {e}")
        await processing_msg.edit_text(f"❌ Error: I couldn't process this link. Make sure it's valid and from a supported platform.\n\nTechnical details: {str(e)[:100]}...")


# Handle button callbacks
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Handle cancel button
    if data == "cancel":
        await query.message.edit_caption(
            caption=query.message.caption + "\n\n❌ Download cancelled.",
            reply_markup=None
        )
        return
    
    # Handle delete button from /list command
    if data.startswith("delete|"):
        index = int(data.split("|")[1])
        downloads = context.user_data.get('downloads', [])
        if 0 <= index < len(downloads):
            del downloads[index]
            context.user_data['downloads'] = downloads
            await query.message.edit_caption(
                caption="✅ Entry removed from your download history.",
                reply_markup=None
            )
        return
    
    # Extract action and URL from callback data
    action, url = data.split('|')
    
    # Create a temporary directory for downloads if it doesn't exist
    download_dir = "./downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # Use simple file naming approach
    file_id = f"{query.from_user.id}_{int(time.time())}"
    filename = f"downloads/download_{file_id}"
    output = f"{filename}.mp4" if action == "video" else f"{filename}.mp3"
    
    # Log the file path for debugging
    logger.info(f"Download path: {output}")
    
    # Send progress message
    progress_msg = await query.message.reply_text("⏳ Starting download...")
    
    # Function to update progress message
    async def edit_progress_message(text):
        try:
            await progress_msg.edit_text(text)
        except Exception as e:
            logger.error(f"Failed to update progress message: {e}")
    
    # Progress hook for yt-dlp
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            downloaded = round(d.get('downloaded_bytes', 0) / 1024 / 1024, 2)
            total = round(d.get('total_bytes', 1) / 1024 / 1024, 2) if d.get('total_bytes') else 0
            eta = d.get('eta', '?')
            msg = f"⏳ Downloading: {percent} ({downloaded} MB / {total} MB)\nETA: {eta}s"
            context.application.create_task(edit_progress_message(msg))
    
    # Set yt-dlp options with simpler formats
    ydl_opts = {
        'outtmpl': output,
        'format': 'best' if action == 'video' else 'bestaudio',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }] if action == 'audio' else [],
        'progress_hooks': [progress_hook],
        'noplaylist': True
    }
    
    try:
        # Download file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        await edit_progress_message("✅ Download complete! Uploading to GoFile...")
        
        # Upload to GoFile
        with open(output, 'rb') as f:
            resp = requests.post("https://store1.gofile.io/uploadFile", files={'file': f})
        
        json_resp = resp.json()
        
        if json_resp.get('status') != 'ok':
            raise Exception(f"GoFile upload failed: {json_resp.get('status')}")
        
        dl_url = json_resp.get('data', {}).get('downloadPage')
        
        if not dl_url:
            raise Exception("Upload failed: No download URL received")
        
        # Get metadata from user context
        meta = context.user_data.get('meta', {})
        title = meta.get('title', 'Unknown Title')
        duration = meta.get('duration', 'N/A')
        platform = meta.get('platform', 'Unknown')
        thumbnail = meta.get('thumbnail')
        
        # Add to download history
        downloads = context.user_data.get('downloads', [])
        downloads.append({
            "title": title,
            "platform": platform,
            "duration": duration,
            "thumbnail": thumbnail,
            "link": dl_url,
            "type": "Video" if action == "video" else "Audio"
        })
        context.user_data['downloads'] = downloads[-10:]  # Keep only last 10
        
        # Send success message
        caption = (
            f"*{title}*\n\n"
            f"📺 Platform: {platform}\n"
            f"⏱ Duration: {duration}\n"
            f"📦 Type: {'Video' if action == 'video' else 'Audio (MP3)'}\n\n"
            f"✅ Your download is ready!"
        )
        
        button = InlineKeyboardMarkup([[InlineKeyboardButton("Download Now 📥", url=dl_url)]])
        
        await progress_msg.delete()
        await query.message.reply_photo(
            photo=thumbnail,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=button
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await edit_progress_message(f"❌ Download failed: {str(e)[:100]}...")
    
    finally:
        # Clean up temporary files
        if os.path.exists(output):
            try:
                os.remove(output)
                logger.info(f"Removed temporary file: {output}")
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")


# List downloads command
async def list_downloads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's download history."""
    downloads = context.user_data.get('downloads', [])
    
    if not downloads:
        await update.message.reply_text("📂 You haven't downloaded anything yet. Send me a link to get started!")
        return
    
    await update.message.reply_text(
        f"📋 Your download history ({len(downloads)} items):",
        parse_mode="Markdown"
    )
    
    for i, item in enumerate(downloads):
        caption = (
            f"*{item['title']}*\n\n"
            f"📺 Platform: {item['platform']}\n"
            f"⏱ Duration: {item['duration']}\n"
            f"📦 Type: {item['type']}"
        )
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Download 📥", url=item['link'])],
            [InlineKeyboardButton("Delete from list ❌", callback_data=f"delete|{i}")]
        ])
        
        await update.message.reply_photo(
            photo=item['thumbnail'],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=buttons
        )


# Cleanup command
async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the user's download history."""
    context.user_data['downloads'] = []
    await update.message.reply_text("✅ Your download history has been cleared.")


# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send message to user only if update is available
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, something went wrong. Please try again later."
        )


# Keep alive command to prevent bot timeout
async def keep_alive(context: ContextTypes.DEFAULT_TYPE):
    """Send a periodic ping to keep the bot running 24/7."""
    logger.info("Sending keep-alive ping...")
    
    # You can add any periodic maintenance tasks here
    # For example, cleaning up old temporary files
    try:
        if os.path.exists("downloads"):
            for file in os.listdir("downloads"):
                file_path = os.path.join("downloads", file)
                file_age = time.time() - os.path.getmtime(file_path)
                # Delete files older than 1 hour (3600 seconds)
                if file_age > 3600 and os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed old temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error during keep-alive maintenance: {e}")

def main():
    """Start the bot."""
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_downloads))
    application.add_handler(CommandHandler("cleanup", cleanup))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Add the keep-alive job (runs every 5 minutes)
    job_queue = application.job_queue
    job_queue.run_repeating(keep_alive, interval=300, first=10)
    
    # Start the Bot
    logger.info("Starting bot with 24/7 keep-alive...")
    application.run_polling()


if __name__ == '__main__':
    main()
