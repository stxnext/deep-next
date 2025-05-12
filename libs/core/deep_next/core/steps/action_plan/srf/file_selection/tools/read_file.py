from pathlib import Path
from typing import Annotated

from deep_next.core.io import read_txt
from deep_next.core.steps.action_plan.srf.file_selection.tools.module_public_interface_lookup import (  # noqa: E501
    module_public_interface_lookup_tool_builder,
)
from langchain_core.tools import tool

MAX_LINES = 1000


def read_file_or_lookup_interface(root_path: Path, file_path: str) -> str:
    """Read the contents of a text file and return it as a string.

    If the file has more than {MAX_LINES} lines, return the module public interface
    lookup tool.
    """
    try:
        txt = read_txt(path=root_path / file_path)
    except FileNotFoundError:
        return f"File not found: {file_path}"

    lines = txt.split("\n")

    if len(lines) > MAX_LINES:
        return module_public_interface_lookup_tool_builder(root_path).invoke(file_path)

    # add line numbers to the text.
    txt = "\n".join([f"{str(i).rjust(4)}: {line}" for i, line in enumerate(lines, 1)])
    return txt


def read_file_tool_builder(root_path: Path):
    """Build a tool to read a file."""

    @tool
    def read_file(
        file_path: Annotated[str, "Path to text file."]
    ) -> Annotated[str, "The contents of the text file."]:
        """
        Read file or return public interface if it's too long.

        Read the contents of a text file and return it as a string. If the file
        exceeds {MAX_LINES} lines, a public interface of the *.py file will be
        returned.
        """
        return read_file_or_lookup_interface(root_path, file_path)

    return read_file
