import telebot
from telebot import types
import os
import tempfile
from downloader import download_media, is_valid_url
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}  # To store user-selected URL

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Welcome! Send a YouTube, Instagram, or social media link to begin.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()

    if not is_valid_url(url):
        bot.reply_to(message, "❌ Please send a valid URL from YouTube, Instagram, Facebook, etc.")
        return

    user_sessions[message.chat.id] = {'url': url}

    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
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
        error_message = download_info.get("error", "Unknown error")
        print(">>> Download failed with:", error_message)
        bot.edit_message_text(f"❌ Download failed: {error_message}", chat_id, msg.message_id)
        return

    file_path = download_info['file_path']
    title = download_info.get('title', 'Downloaded Media')

    with open(file_path, 'rb') as f:
        if format_type == 'video':
            bot.send_video(chat_id, video=f, caption=title)
        else:
            bot.send_audio(chat_id, audio=f, caption=title)

    bot.edit_message_text("✅ Download complete!", chat_id, msg.message_id)

except Exception as e:
    print(">>> Download crashed with exception:", str(e))
    bot.edit_message_text("❌ Download failed. Please try a different link or format.", chat_id, msg.message_id)

finally:
    try:
        for file in os.listdir(user_temp_dir):
            os.remove(os.path.join(user_temp_dir, file))
        os.rmdir(user_temp_dir)
    except Exception:
        pass

# Start bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()

bot.edit_message_text("✅ Download complete!", chat_id, msg.message_id)

    except Exception as e:
        print(">>> Download crashed with exception:", str(e))
        bot.edit_message_text("❌ Download failed. Please try a different link or format.", chat_id, msg.message_id)

    finally:
        try:
            for file in os.listdir(user_temp_dir):
                os.remove(os.path.join(user_temp_dir, file))
            os.rmdir(user_temp_dir)
        except Exception:
            pass

# === Start bot when this file is run ===
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()

try:
        download_info = download_media(url, format_type, user_temp_dir)

        if 'error' in download_info:
            error_message = download_info.get("error", "Unknown error")
            print(">>> Download failed with:", error_message)
            bot.edit_message_text(f"❌ Download failed: {error_message}", chat_id, msg.message_id)
            return

        file_path = download_info['file_path']
        title = download_info.get('title', 'Downloaded Media')

        with open(file_path, 'rb') as f:
            if format_type == 'video':
                bot.send_video(chat_id, video=f, caption=title)
            else:
                bot.send_audio(chat_id, audio=f, caption=title)

        bot.edit_message_text("✅ Download complete!", chat_id, msg.message_id)

    except Exception as e:
        print(">>> Download crashed with exception:", str(e))
        bot.edit_message_text("❌ Download failed. Please try a different link or format.", chat_id, msg.message_id)

    finally:
        try:
            for file in os.listdir(user_temp_dir):
                os.remove(os.path.join(user_temp_dir, file))
            os.rmdir(user_temp_dir)
        except Exception:
            pass
