import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Define log formats
CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FILE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

def setup_logging():
    # Create formatters
    console_formatter = logging.Formatter(CONSOLE_FORMAT)
    file_formatter = logging.Formatter(FILE_FORMAT)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "app.log"),
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set up specific loggers
    loggers = {
        "app": logging.getLogger("app"),
        "app.api": logging.getLogger("app.api"),
        "app.services": logging.getLogger("app.services"),
        "uvicorn": logging.getLogger("uvicorn"),
        "fastapi": logging.getLogger("fastapi")
    }

    for logger in loggers.values():
        logger.setLevel(logging.INFO)

    return loggers