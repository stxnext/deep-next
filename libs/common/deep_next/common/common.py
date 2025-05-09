from dotenv import load_dotenv
from loguru import logger


def load_monorepo_dotenv() -> None:
    """Loads the .env file from the monorepo root and sets Loguru log level."""
    import os
    from deep_next.common.config import MONOREPO_ROOT_PATH

    path = MONOREPO_ROOT_PATH / ".env"

    if not path.exists():
        raise FileNotFoundError(f"No .env file found: {path}")

    assert load_dotenv(path, verbose=True, override=True)

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)
    logger.debug(f"Loading .env file: '{str(path)}' with LOG_LEVEL={log_level}")


def gitignore_name(name: str) -> str:
    """Converts the name so that it'll be ignored by git."""
    from deep_next.common.config import MONOREPO_ROOT_PATH

    with open(MONOREPO_ROOT_PATH / ".gitignore", "r") as f:
        if "___*" not in f.read():
            raise ValueError(
                "The gitignore file does not contain expected pattern '___*'"
            )

    return f"___{name}"
