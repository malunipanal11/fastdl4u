import telebot
from telebot import types
import os
from downloader import download_media, is_valid_url
from dotenv import load_dotenv
import tempfile

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Welcome! Send a YouTube, Instagram, or social media link to begin.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not is_valid_url(url):
        bot.reply_to(message, "❌ Please send a valid URL from YouTube, Instagram, etc.")
        return

    user_sessions[message.chat.id] = {'url': url}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Video", callback_data="video"),
        types.InlineKeyboardButton("Audio", callback_data="audio")
    )
    bot.send_message(message.chat.id, "Choose format to download:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    format_type = call.data
    chat_id = call.message.chat.id
    url = user_sessions.get(chat_id, {}).get('url')

    if not url:
        bot.send_message(chat_id, "❌ Session expired. Please send the link again.")
        return

    msg = bot.send_message(chat_id, "⏬ Downloading, please wait...")
    user_temp_dir = tempfile.mkdtemp()

    try:
        download_info = download_media(url, format_type, user_temp_dir)

        if 'error' in download_info:
            bot.edit_message_text(f"❌ Download failed: {download_info['error']}", chat_id, msg.message_id)
            return

        with open(download_info['file_path'], 'rb') as f:
            if format_type == 'video':
                bot.send_video(chat_id, f, caption=download_info['title'])
            else:
                bot.send_audio(chat_id, f, caption=download_info['title'])

        bot.edit_message_text("✅ Download complete!", chat_id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, msg.message_id)

    finally:
        try:
            for f in os.listdir(user_temp_dir):
                os.remove(os.path.join(user_temp_dir, f))
            os.rmdir(user_temp_dir)
        except Exception:
            pass
