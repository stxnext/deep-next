import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deep_next.connectors.version_control_provider import BaseMR

DEEP_NEXT_PR_DESCRIPTION = "DeepNext's attempt to solve the issue #{issue_no}."


def extract_issue_number_from_mr(mr: 'BaseMR'):

    to_replace = r"{issue_no}"
    replace_with = r"(\d+)"
    pattern = DEEP_NEXT_PR_DESCRIPTION.replace(to_replace, replace_with)

    match = re.search(pattern, mr.description)

    if match:
        return int(match.group(1))

    return None


def is_snake_case(txt: str) -> bool:
    """Makes sure that the given string is in snake_case."""
    snake_case_pattern = r"^[a-z0-9]+(_[a-z0-9]+)*$"
    return bool(re.match(snake_case_pattern, txt))


def format_comment_with_header(comment: str) -> str:
    """Format the content with a header."""
    return f"## 🚧 DeepNext status update\n\n{comment}"
