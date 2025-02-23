import logging
import os
from logging.handlers import RotatingFileHandler

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
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Configure formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)

    # Main log file
    main_log_file = os.path.join(logs_dir, "app.log")
    file_handler = RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(detailed_formatter)

    # Debug log file
    debug_log_file = os.path.join(logs_dir, "debug.log")
    debug_handler = RotatingFileHandler(
        debug_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    debug_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure specific loggers
    loggers = {
        "app": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.api": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.services": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.services.pdf_service": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
        "app.services.rag_pipeline": {"level": logging.DEBUG, "handlers": ["console", "file", "debug"]},
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

        # Prevent propagation to root logger
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    logger = logging.getLogger(name)

    # If logger doesn't have any handlers, add them
    if not logger.handlers:
        setup_logging()

    return logger
