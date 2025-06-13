import ast
import re
from dataclasses import dataclass
from pprint import pformat
from typing import TextIO

LINTER_ERROR = "LINTER_ERROR"
FAILED_TO_MATCH = "FAILED_TO_MATCH"


MODIFICATIONS_TAG = "modifications"


@dataclass
class Edit:
    filename: str
    before: str
    after: str

    def __str__(self):
        return (
            f"{self.filename}"
            f"\nBefore:\n{pformat(self.before)}"
            f"\nAfter:\n{pformat(self.after)}\n"
        )

    def __repr__(self):
        return str(self)


class Writable(TextIO):
    """dummy output stream for pylint"""

    def __init__(self) -> None:
        self.content: list[str] = []

    def write(self, s: str) -> int:
        self.content.append(s)
        return len(s)

    def read(self, n: int = 0) -> str:
        return "\n".join(self.content)


def lint_python_content(content: str) -> bool:
    """Check if Python content has valid syntax.

    Args:
        content: Python source code as string

    Returns:
        True if syntax is valid, False otherwise.
    """
    try:
        ast.parse(content)
        compile(content, "<string>", "exec")
        return True
    except (SyntaxError, IndentationError):
        return False


def parse_edits(chat_string: str) -> list[Edit]:
    """
    Parse edits from a chat string.

    This function extracts code edits from a chat string and returns them as a list
    of Edit objects.

    Args:
        chat_string (str): The chat content containing code edits.

    Returns:
        List[Edit]: A list of Edit objects representing the parsed code edits.
    """

    def parse_in_fence(lines: list[str]):
        """New version of parsing multiple edits within one fence."""
        # remove obviously suspicious lines
        sus_contents = ["# Rest of the code..."]
        lines = [line for line in lines if line.strip() not in sus_contents]

        file_start = "<file>"
        file_end = "</file>"
        original_start = "<original>"
        original_end = "</original>"
        patched_start = "<patched>"
        patched_end = "</patched>"

        all_edits: list[Edit] = []
        content = "\n".join(lines)

        # use regex to find content between <file> and </file>
        file_pattern = re.compile(f"{file_start}(.*?){file_end}", re.DOTALL)
        original_pattern = re.compile(f"{original_start}(.*?){original_end}", re.DOTALL)
        patched_pattern = re.compile(f"{patched_start}(.*?){patched_end}", re.DOTALL)

        file_matches = file_pattern.findall(content)
        original_matches = original_pattern.findall(content)
        patched_matches = patched_pattern.findall(content)

        for file, original, patched in zip(
            file_matches, original_matches, patched_matches
        ):
            file = file.strip()
            original = original.strip("\n")
            patched = patched.strip("\n")
            all_edits.append(Edit(file, original, patched))

        return all_edits

    edits = []
    current_edit = []
    in_fence = False

    for line in chat_string.split("\n"):
        if line.startswith(f"</{MODIFICATIONS_TAG}>") and in_fence:
            edits.extend(parse_in_fence(current_edit))
            current_edit = []
            in_fence = False
            continue
        elif line.startswith(f"<{MODIFICATIONS_TAG}>") and not in_fence:
            in_fence = True
            continue
        if in_fence:
            current_edit.append(line)

    return edits
