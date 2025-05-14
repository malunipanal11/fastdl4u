from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy without a specific app (we'll set it up later)
db = SQLAlchemy()

class User(db.Model):
    """User model to store Telegram user information."""
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(120), nullable=True)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with downloads
    downloads = db.relationship('Download', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.telegram_id} - {self.username or self.first_name}>'

class Download(db.Model):
    """Download model to store information about downloaded media."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    format_type = db.Column(db.String(20), nullable=False)  # 'video' or 'audio'
    title = db.Column(db.String(200), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)  # Size in bytes
    download_time = db.Column(db.Float, nullable=True)  # Time taken to download in seconds
    status = db.Column(db.String(20), nullable=False, default='started')  # 'started', 'completed', 'failed'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Download {self.id} - {self.platform} {self.format_type}>'