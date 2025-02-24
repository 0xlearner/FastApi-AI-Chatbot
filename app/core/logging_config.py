import logging
import sys
from typing import Dict


class LoggerSingleton:
    _instances: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        if name not in cls._instances:
            logger = logging.getLogger(name)

            # Remove any existing handlers
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            # Create formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
            )

            # Create console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)

            # Add handler to logger
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)

            # Store the instance
            cls._instances[name] = logger

        return cls._instances[name]


def get_logger(name: str) -> logging.Logger:
    return LoggerSingleton.get_logger(name)
