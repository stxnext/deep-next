from pathlib import Path
import os
from loguru import logger

from deep_next.common.common import gitignore_name

MONOREPO_ROOT_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent

MONOREPO_DATA_PATH = MONOREPO_ROOT_PATH / gitignore_name("data")


def setup_logging() -> None:
    """Configure loguru logger using LOG_LEVEL env variable (default: INFO)."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    # Remove all existing handlers to ensure idempotency
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)
