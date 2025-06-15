from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from downloader import download_all_assets
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    meta = download_all_assets(url)

    caption = f"🎬 *{meta['title']}*\\n🕒 {meta['duration']}s | 📦 {(meta['size']/1_000_000):.2f} MB\\n📺 {meta['quality']} | 🌐 {meta['platform']}"
    
    await update.message.reply_photo(photo=open(meta['thumbnail'][1:], 'rb'), caption=caption, parse_mode="Markdown")
    await update.message.reply_video(video=open(meta['video_file'], 'rb'), caption="📹 Ultra HD Video")
    await update.message.reply_audio(audio=open(meta['audio_file'], 'rb'), caption="🎵 High-Res Audio")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle))

if __name__ == "__main__":
    app.run_polling()
