import re
from datetime import datetime

DEEP_NEXT_PR_DESCRIPTION = "DeepNext's attempt to solve the issue #{issue_no}."


FEATURE_BRANCH_NAME_TMPL = "deep_next/issue_{issue_no}/{note}"


def create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def is_snake_case(txt: str) -> bool:
    """Makes sure that the given string is in snake_case."""
    snake_case_pattern = r"^[a-z0-9]+(_[a-z0-9]+)*$"
    return bool(re.match(snake_case_pattern, txt))


_COMMENT_HEADER = "## 🚧 DeepNext status update"


def format_comment_with_header(comment: str) -> str:
    """Format the content with a header."""
    return f"{_COMMENT_HEADER}\n\n{comment}"


def trim_comment_header(comment: str) -> str:
    """Trims the header from the comment."""
    if comment.startswith(_COMMENT_HEADER):
        return comment[len(_COMMENT_HEADER) :].strip()

    return comment
