import os
import textwrap

from dotenv import load_dotenv
from loguru import logger


def load_monorepo_dotenv() -> None:
    """Loads the .env file from the monorepo root."""
    from deep_next.common.config import MONOREPO_ROOT_PATH

    path = MONOREPO_ROOT_PATH / ".env"

    if not path.exists():
        raise FileNotFoundError(f"No .env file found: {path}")

    logger.debug(f"Loading .env file: '{str(path)}'")

    assert load_dotenv(path, verbose=True, override=True)


def configure_logging_from_env() -> None:
    """Configures Loguru log level from LOG_LEVEL env var (default: INFO)."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    # Remove all existing handlers to ensure idempotency
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


def prepare_issue_statement(
    issue_title: str,
    issue_description: str,
    issue_comments: list[str],
) -> str:
    """Prepares the issue statement for the model."""
    if not issue_title:
        issue_title = "<No title>"

    if not issue_description:
        issue_description = "<No description>"

    if not issue_comments:
        issue_comments_str = "<No comments>"
    else:
        issue_comments_str = "\n\n".join([f"- {comment}" for comment in issue_comments])

    return textwrap.dedent(
        f"""\
        # Issue title:
        {issue_title}

        # Issue description:
        {issue_description}

        # Issue comment:
        {issue_comments_str}
        """
    )
