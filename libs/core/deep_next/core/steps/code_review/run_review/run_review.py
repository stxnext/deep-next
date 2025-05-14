from pathlib import Path

from deep_next.core.steps.code_review.run_review.lint import Flake8CodeReviewer
from deep_next.core.steps.code_review.run_review.llm import (
    CodeStyleCodeReviewer,
    DiffConsistencyCodeReviewer,
)
from loguru import logger

all_reviewers = [
    CodeStyleCodeReviewer(),
    DiffConsistencyCodeReviewer(),
    Flake8CodeReviewer(),
]


def run_review(
    root_path: Path,
    issue_statement: str,
    project_knowledge: str,
    git_diff: str,
    code_fragments: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, bool]]:

    issues = {code_reviewer.name: [] for code_reviewer in all_reviewers}
    review_completed = {code_reviewer.name: True for code_reviewer in all_reviewers}

    for code_reviewer in all_reviewers:
        try:
            _issues = code_reviewer.run(
                root_path,
                issue_statement,
                project_knowledge,
                git_diff,
                code_fragments,
            )

            issues[code_reviewer.name].extend(_issues)
        except Exception as e:
            logger.warning(
                f"Code reviewer {code_reviewer.name} failed to review the code. "
                f"Exception:\n{e}"
            )
            review_completed[code_reviewer.name] = False

    return issues, review_completed
