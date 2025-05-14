from abc import ABC, abstractmethod
from pathlib import Path


class BaseCodeReviewer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the code reviewer."""

    @abstractmethod
    def run(
        self,
        root_path: Path,
        issue_statement: str,
        project_knowledge: str,
        git_diff: str,
        code_fragments: dict[str, list[str]],
    ) -> list[str]:
        """Run the linter on the given code and return the issues found."""
