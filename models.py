"""
Jarvis SaaS Models - Persistent User and Conversation tracking.
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # SaaS & Subscription Foundation
    tier = db.Column(db.String(32), default='free') # free, pro, unlimited
    credits = db.Column(db.Integer, default=50)
    last_reset = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # User Preferences (The Adaptive Memory aspect)
    preferences = db.Column(db.JSON, default={})
    
    # Relationships
    conversations = db.relationship('Conversation', backref='author', lazy='dynamic', cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_unlimited(self):
        """Check if user has unlimited access (Admin or special tier)."""
        return self.username == 'Admin' or self.tier == 'unlimited'

    @property
    def is_admin(self):
        """Check if user has administrative authority."""
        return self.username == 'Admin' or self.username == 'Ayush' or self.tier == 'unlimited'

    def has_credits(self, amount=1):
        """Check if user has enough credits for an operation."""
        if self.is_unlimited:
            return True
        return self.credits >= amount

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Message History stored as JSON for flexibility
    history = db.Column(db.JSON, default=[])

    def __init__(self, **kwargs):
        super(Conversation, self).__init__(**kwargs)

class Mission(db.Model):
    __tablename__ = 'missions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(32), default='pending') # pending, active, completed, failed
    priority = db.Column(db.Integer, default=1)
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    progress = db.Column(db.Integer, default=0)

    def __init__(self, **kwargs):
        super(Mission, self).__init__(**kwargs)

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    status = db.Column(db.String(32), default='draft') # draft, rendering, completed, failed
    progress = db.Column(db.Integer, default=0)
    final_video_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    scenes = db.relationship('ProjectScene', backref='project', lazy=True, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)

class ProjectScene(db.Model):
    __tablename__ = 'project_scenes'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(32), db.ForeignKey('projects.id'), nullable=False)
    index = db.Column(db.Integer, nullable=False)
    narration = db.Column(db.Text, nullable=False)
    visual_prompt = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(512))
    audio_url = db.Column(db.String(512))
    clip_url = db.Column(db.String(512))

    def __init__(self, **kwargs):
        super(ProjectScene, self).__init__(**kwargs)

class Rating(db.Model):
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(64), nullable=False) # 'message', 'image', 'video', 'intel', 'system'
    target_id = db.Column(db.String(256), nullable=False)   # Unique key per target (e.g. filename, msg_id)
    score = db.Column(db.Integer, nullable=False)          # 1 to 5 stars
    feedback = db.Column(db.Text, nullable=True)           # Optional comments
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super(Rating, self).__init__(**kwargs)

class AppConnector(db.Model):
    __tablename__ = 'app_connectors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(64), nullable=False) # e.g., 'github', 'google workspace'
    is_active = db.Column(db.Boolean, default=False)
    command = db.Column(db.String(256), nullable=True)  # e.g., 'npx'
    args = db.Column(db.JSON, default=[])               # e.g., ['-y', '@modelcontextprotocol/server-github']
    env_vars = db.Column(db.JSON, default={})           # Any secret env vars required
    scopes = db.Column(db.JSON, default=[])             # Granted permissions/scopes
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super(AppConnector, self).__init__(**kwargs)
