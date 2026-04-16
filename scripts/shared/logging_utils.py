"""Logging helpers for the pipeline scaffold."""

import logging
from pathlib import Path


def get_logger(name, level="INFO", log_file_path=None):
    """Create a basic stdout logger and optional file logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    resolved_level = getattr(logging, str(level).upper(), logging.INFO)
    logger.setLevel(resolved_level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file_path:
        log_file_path = Path(log_file_path)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
