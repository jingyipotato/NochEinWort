"""Script for logging."""

import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Return a formatted logger.

    Args:
        name: Name of the logger.

    Returns:
        Configured logger instance.

    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger