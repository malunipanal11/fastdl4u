import os
import json
import threading
import requests
from flask import Flask, request, jsonify, render_template
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import yt_dlp

app = Flask(__name__)
file_log = 'file_log.json'
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = Bot(BOT_TOKEN)

if not os.path.exists(file_log):
    with open(file_log, 'w') as f:
        json.dump([], f)

def save_to_log(data):
    with open(file_log, 'r+') as f:
        logs = json.load(f)
        logs.append(data)
        f.seek(0)
        json.dump(logs, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/file_log.json')
def log_file():
    with open(file_log) as f:
        return jsonify(json.load(f))

@app.route('/api/process', methods=['POST'])
def process():
    content = request.json
    url = content['link']
    format = content['format']

    ydl_opts = {
        'format': 'bestaudio' if format == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': '%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'writethumbnail': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }] if format == 'audio' else []
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).replace('webm', 'mp4')

    with open(filename, 'rb') as f:
        res = requests.post('https://catbox.moe/user/api.php',
            files={'fileToUpload': f},
            data={'reqtype': 'fileupload'})
        file_url = res.text

    file_data = {
        'filename': filename,
        'file_url': file_url,
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'duration': str(info.get('duration', '')) + ' sec',
        'quality': info.get('format'),
        'size': f"{round(info.get('filesize', 0) / 1024 / 1024, 2)} MB" if info.get('filesize') else 'Unknown'
    }
    save_to_log(file_data)

    return jsonify({**file_data, 'catbox_url': file_url})

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("Processing your link...")

    for fmt in ['audio', 'video']:
        resp = requests.post('http://localhost:5000/api/process', json={'link': url, 'format': fmt})
        if resp.status_code != 200:
            continue
        data = resp.json()
        with open(data['filename'], 'rb') as f:
            await update.message.reply_video(
                f,
                caption=f"🎬 {data['title']}\n⏱ {data['duration']}\n💾 {data['size']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Play", url=data['file_url'])],
                    [InlineKeyboardButton("⬇ Download", url=data['file_url'])],
                    [InlineKeyboardButton("❌ Delete", callback_data='delete')]
                ])
            )
        break

async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(debug=False, host='0.0.0.0')).start()
    import asyncio
    asyncio.run(main())
