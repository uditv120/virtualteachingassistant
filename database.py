import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_database(app):
    """Initialize database with Flask app"""
    # Check if DATABASE_URL is available
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # initialize the app with the extension
    db.init_app(app)
    
    with app.app_context():
        # Import models to register tables
        from models import Question, SystemStats, DocumentIndex, UserFeedback
        
        # Create all tables
        db.create_all()
        
    return db