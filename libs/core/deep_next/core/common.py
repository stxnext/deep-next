import re
import textwrap
import os
from pathlib import Path

from deep_next.core.io import read_txt
from langchain_core.output_parsers import BaseOutputParser


def setup_logger() -> None:
    """Configures the Loguru logger with env-based log level and standard options."""
    from loguru import logger
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )


# TODO: Remove. It's moved to common lib.
def gitignore_name(name: str) -> str:
    """Converts the name so that it'll be ignored by git."""
    return f"___{name}"


def dump_filepaths(file_paths: list[Path | str]) -> str:
    """Create a dump of the contents of the given file paths."""
    file_repr_tmpl = textwrap.dedent(
        """
        Path: {abs_path}
        ```python
        {code}
        ```
        """
    )
    file_paths = [str(Path(path).resolve()) for path in file_paths]

    dump = [
        file_repr_tmpl.format(abs_path=file_path, code=read_txt(file_path))
        for file_path in file_paths
    ]

    return "\n".join(dump)


class RemoveThinkingBlocksParser(BaseOutputParser):
    """Parser that removes <think>...</think> blocks from LLM output."""

    def parse(self, text: str) -> str:
        """Remove <think>...</think> blocks from text.

        Args:
            text: The input string with potential <think>...</think> blocks

        Returns:
            The text with <think>...</think> blocks removed
        """
        # Pattern to match <think>...</think> blocks (handling multiline content)
        pattern = r"<think>.*?</think>"
        # Remove the blocks using regex with DOTALL flag to match across newlines
        cleaned_text = re.sub(pattern, "", text, flags=re.DOTALL)
        return cleaned_text.strip()
