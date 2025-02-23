import os
from app.db.init_db import init_db
from app.core.config import settings


def initialize_application():
    """Initialize the application by setting up necessary directories and database"""
    # Create uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize database
    init_db()

    print("Application initialized successfully!")
    print(f"Database file: {settings.DATABASE_URL.replace('sqlite:///', '')}")
    print(f"Uploads directory: {settings.UPLOAD_DIR}")
