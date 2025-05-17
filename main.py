from flask import Flask, request
import os
from telebot import types
from bot import bot  # your bot instance

WEBHOOK_PATH = f"/{os.getenv('BOT_TOKEN')}"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot is live via webhook!'

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        bot.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
        return '', 200
    else:
        return 'Unsupported Content-Type', 403

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set:", WEBHOOK_URL)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
