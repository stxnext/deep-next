from dotenv import load_dotenv
from loguru import logger


def load_monorepo_dotenv() -> None:
    """Loads the .env file from the monorepo root and configures logging."""
    from deep_next.common.config import MONOREPO_ROOT_PATH
    import os

    path = MONOREPO_ROOT_PATH / ".env"

    if not path.exists():
        raise FileNotFoundError(f"No .env file found: {path}")

    logger.debug(f"Loading .env file: '{str(path)}'")

    assert load_dotenv(path, verbose=True, override=True)

    # Configure Loguru logging level based on LOG_LEVEL env variable
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)


def gitignore_name(name: str) -> str:
    """Converts the name so that it'll be ignored by git."""
    from deep_next.common.config import MONOREPO_ROOT_PATH

    with open(MONOREPO_ROOT_PATH / ".gitignore", "r") as f:
        if "___*" not in f.read():
            raise ValueError(
                "The gitignore file does not contain expected pattern '___*'"
            )

    return f"___{name}"
