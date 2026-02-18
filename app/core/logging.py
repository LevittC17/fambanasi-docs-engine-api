"""
Logging configuration module.

Provides structured logging setup with support for JSON formatting,
multiple handlers, and integration with monitoring services.
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Sets up logging handlers, formatters, and levels based on
    application settings. In production, uses JSON formatting
    for better log aggregation.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if configured)
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance configured for the module
    """
    return logging.getLogger(name)
