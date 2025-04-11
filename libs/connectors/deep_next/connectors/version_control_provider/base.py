import textwrap
from abc import ABC, abstractmethod
from datetime import datetime


class BaseIssue(ABC):
    @property
    @abstractmethod
    def url(self) -> str:
        """"""

    @property
    @abstractmethod
    def labels(self) -> list[str]:
        """"""

    @property
    @abstractmethod
    def no(self) -> int:
        """"""

    @property
    @abstractmethod
    def title(self) -> str:
        """"""

    @property
    @abstractmethod
    def description(self) -> str:
        """"""

    @property
    @abstractmethod
    def comments(self) -> str:
        """"""

    @abstractmethod
    def add_comment(
        self, comment: str, file_content: str | None = None, file_name="content.txt"
    ) -> None:
        """"""

    @abstractmethod
    def add_label(self, label: str) -> None:
        """"""

    @abstractmethod
    def remove_label(self, label: str) -> None:
        """"""

    @property
    def _comment_prefix(self) -> str:
        return "[DeepNext]"

    @property
    def comment_thread_header(self):
        return f"## 🚧 DeepNext WIP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"

    def has_label(self, label: str) -> bool:
        """"""
        return label in self.labels

    @staticmethod
    def prettify_comment(txt: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return textwrap.dedent(
            f"""\
            **Status update ({timestamp}):**

            > {txt}
            """
        )


class BaseMR(ABC):
    @property
    @abstractmethod
    def url(self) -> str:
        """"""

    @property
    @abstractmethod
    def no(self) -> int:
        """"""

    @property
    @abstractmethod
    def title(self) -> str:
        """"""

    @property
    @abstractmethod
    def description(self) -> str:
        """"""

    @property
    @abstractmethod
    def base_commit(self) -> str:
        """Base commit for MR (the one on which changes are applied)."""

    @property
    @abstractmethod
    def git_diff(self) -> str:
        """Retrieve the full git diff for a given merge request."""


class BaseConnector(ABC):
    @abstractmethod
    def list_issues(self, label=None) -> list[BaseIssue]:
        """Fetches all issues"""

    @abstractmethod
    def get_issue(self, issue_no: int) -> BaseIssue:
        """Fetches a single issue."""

    @abstractmethod
    def get_mr(self, mr_no: int) -> BaseMR:
        """Fetches a single merge request."""

    @abstractmethod
    def create_mr(self, merge_branch: str, into_branch: str, title: str) -> BaseMR:
        """Creates new merge request."""
