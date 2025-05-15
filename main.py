from flask import Flask
import os
import logging
import bot  # importing starts the bot (infinity_polling)

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("Using BOT_TOKEN:", BOT_TOKEN)

# Optional: Render may require a web service to stay live
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy with the app
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Define a function to get the Flask app instance
# This will be imported by other modules
def get_flask_app():
    return app

# Import the Bot class from the bot module after setting up the app
bot_module = importlib.import_module('bot')
bot_module.Bot.run()
bot = Bot()

@app.route('/')
def home():
    return "Bot is alive!"

@app.route('/stats')
def stats():
    """Display download statistics."""
    with app.app_context():
        total_users = User.query.count()
        total_downloads = Download.query.count()
        completed_downloads = Download.query.filter_by(status='completed').count()
        failed_downloads = Download.query.filter_by(status='failed').count()
        
        platform_stats = db.session.query(
            Download.platform, 
            db.func.count(Download.id)
        ).group_by(Download.platform).all()
        
        format_stats = db.session.query(
            Download.format_type, 
            db.func.count(Download.id)
        ).group_by(Download.format_type).all()
        
        return jsonify({
            'total_users': total_users,
            'total_downloads': total_downloads,
            'completed_downloads': completed_downloads,
            'failed_downloads': failed_downloads,
            'platform_stats': dict(platform_stats),
            'format_stats': dict(format_stats)
        })

@app.route('/recent-downloads')
def recent_downloads():
    """Display recent downloads."""
    with app.app_context():
        downloads = Download.query.order_by(Download.created_at.desc()).limit(10).all()
        result = []
        
        for download in downloads:
            result.append({
                'id': download.id,
                'platform': download.platform,
                'format_type': download.format_type,
                'title': download.title,
                'status': download.status,
                'created_at': download.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify(result)

def start_bot():
    """Start the Telegram bot in a separate thread."""
    try:
        bot.run()
    except Exception as e:
        logger.error(f"Error starting the bot: {str(e)}")

# Start the bot in a separate thread when the app is imported
bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

# Run the app when this file is executed directly
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
import bot
bot.bot.infinity_polling()
