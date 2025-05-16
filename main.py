from flask import Flask, jsonify
import os
import threading
import logging
from flask_sqlalchemy import SQLAlchemy
from models import User, Download
import bot  # This imports your TeleBot instance

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db = SQLAlchemy(app)

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Using BOT_TOKEN:", BOT_TOKEN)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/stats')
def stats():
    with app.app_context():
        total_users = User.query.count()
        total_downloads = Download.query.count()
        completed_downloads = Download.query.filter_by(status='completed').count()
        failed_downloads = Download.query.filter_by(status='failed').count()

        platform_stats = dict(db.session.query(
            Download.platform, db.func.count(Download.id)
        ).group_by(Download.platform).all())

        format_stats = dict(db.session.query(
            Download.format_type, db.func.count(Download.id)
        ).group_by(Download.format_type).all())

        return jsonify({
            'total_users': total_users,
            'total_downloads': total_downloads,
            'completed_downloads': completed_downloads,
            'failed_downloads': failed_downloads,
            'platform_stats': platform_stats,
            'format_stats': format_stats
        })

@app.route('/recent-downloads')
def recent_downloads():
    with app.app_context():
        downloads = Download.query.order_by(Download.created_at.desc()).limit(10).all()
        return jsonify([{
            'id': d.id,
            'platform': d.platform,
            'format_type': d.format_type,
            'title': d.title,
            'status': d.status,
            'created_at': d.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for d in downloads])

def start_bot():
    try:
        import time
        time.sleep(3)  # delay avoids race condition
        bot.infinity_polling()  # <-- fixed line
    except Exception as e:
        logger.error(f"Error starting the bot: {str(e)}")

# Start bot in background
bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

# Start Flask app
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
