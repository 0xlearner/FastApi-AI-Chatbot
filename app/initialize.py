import os

from app.core.config import settings
from app.db.init_db import init_db
from app.utils.logging import get_api_logger

logger = get_api_logger("Initializer")


def initialize_application():
    """Initialize the application by setting up necessary directories and database"""
    # Create uploads directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize database
    init_db()

    logger.info("Application initialized successfully!")
    logger.info(f"Database file: {settings.DATABASE_URL.replace('sqlite:///', '')}")
    logger.info(f"Uploads directory: {settings.UPLOAD_DIR}")
