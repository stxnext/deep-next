import os
from loguru import logger

def configure_logging() -> None:
    """Configure Loguru logger based on LOG_LEVEL env variable."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

# Configure logging on import
configure_logging()
