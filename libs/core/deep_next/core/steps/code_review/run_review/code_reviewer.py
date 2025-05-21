from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

CodeFragments = dict[str, list[str]]


class CodeReviewContext(BaseModel):
    root_path: Path
    issue_statement: str
    project_knowledge: str
    git_diff: str
    code_fragments: CodeFragments


class CodeReviewer(Protocol):
    @property
    def name(self) -> str:
        """Name of the code reviewer."""
        ...

    def run(self, context: CodeReviewContext) -> list[str]:
        """Run the linter on the given code and return the issues found."""
        ...
