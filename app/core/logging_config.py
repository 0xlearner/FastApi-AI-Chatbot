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
FILE_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
DEBUG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - "
    "%(funcName)s - %(message)s"
)


def setup_logging():
    # Create formatters
    console_formatter = logging.Formatter(CONSOLE_FORMAT)
    file_formatter = logging.Formatter(FILE_FORMAT)
    debug_formatter = logging.Formatter(DEBUG_FORMAT)

    # Create handlers
    # Console handler - INFO level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Main log file handler - INFO level
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "app.log"), maxBytes=10485760, backupCount=5  # 10MB
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # Debug log file handler - DEBUG level
    debug_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "debug.log"), maxBytes=10485760, backupCount=5  # 10MB
    )
    debug_handler.setFormatter(debug_formatter)
    debug_handler.setLevel(logging.DEBUG)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(debug_handler)

    # Set up specific loggers
    loggers = {
        "app": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.api": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.services": {
            "level": logging.DEBUG,
            "handlers": ["console", "file", "debug"],
        },
        "app.services.rag_pipeline": {
            "level": logging.DEBUG,
            "handlers": ["console", "file", "debug"],
        },
        "uvicorn": {"level": logging.INFO, "handlers": ["console", "file"]},
        "fastapi": {"level": logging.INFO, "handlers": ["console", "file"]},
    }

    # Configure handlers dictionary
    handlers = {
        "console": console_handler,
        "file": file_handler,
        "debug": debug_handler,
    }

    # Configure each logger
    for logger_name, config in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config["level"])

        # Remove any existing handlers
        logger.handlers = []

        # Add configured handlers
        for handler_name in config["handlers"]:
            logger.addHandler(handlers[handler_name])

        # Prevent propagation to root logger if we're handling it specifically
        logger.propagate = False

    return loggers


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    logger = logging.getLogger(name)

    # If logger doesn't have any handlers, add them
    if not logger.handlers:
        setup_logging()

    return logger
