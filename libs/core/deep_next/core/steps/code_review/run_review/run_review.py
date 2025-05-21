from pydantic import BaseModel, Field

from deep_next.core.common import format_exception
from deep_next.core.steps.code_review.run_review.lint import Flake8CodeReviewer
from deep_next.core.steps.code_review.run_review.llm import (
    CodeStyleCodeReviewer,
    DiffConsistencyCodeReviewer,
)
from loguru import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from deep_next.core.steps.code_review.graph import _State

CODE_REVIEWERS = [
    CodeStyleCodeReviewer(),
    DiffConsistencyCodeReviewer(),
    Flake8CodeReviewer(),
]


class CodeReviewResult(BaseModel):
    issues: dict[str, list[str]] = Field(
        description="Problems found in the code by the code reviewer."
    )
    review_completed: dict[str, bool] = Field(
        description="Whether the code review has been successfully finished."
    )


def run_review(state: '_State') -> CodeReviewResult:
    issues = {code_reviewer.name: [] for code_reviewer in CODE_REVIEWERS}
    review_completed = {code_reviewer.name: True for code_reviewer in CODE_REVIEWERS}

    for code_reviewer in CODE_REVIEWERS:
        try:
            _issues = code_reviewer.run(
                state.root_path,
                state.issue_statement,
                state.project_knowledge,
                state.git_diff,
                state.code_fragments,
            )

            issues[code_reviewer.name].extend(_issues)
        except Exception as e:
            logger.warning(
                f"Code reviewer {code_reviewer.name} failed to review the code. "
                f"Exception:\n{format_exception(e)}"
            )
            review_completed[code_reviewer.name] = False

    return CodeReviewResult(
        issues=issues,
        review_completed=review_completed
    )
