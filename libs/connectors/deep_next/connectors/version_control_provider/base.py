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
        self, 
        comment: str, 
        file_content: str | None = None, 
        file_name: str = "content.txt"
    ) -> None:
        """
        Add a comment to the issue.

        If file_content is provided, attach the file to the comment.
        For GitHub, this is implemented by uploading the file as a Gist and
        including the Gist link in the comment, since GitHub does not support
        native file attachments in issue comments.
        For GitLab, native file attachments are supported and should be used.

        Args:
            comment: The comment text to add.
            file_content: Optional file content to attach.
            file_name: The name of the file to attach (default: "content.txt").
        """

    @abstractmethod
    def add_label(self, label: str) -> None:
        """Add a label to the issue."""

    @abstractmethod
    def remove_label(self, label: str) -> None:
        """Remove a label from the issue."""

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

        wrapped = "\n".join(
            textwrap.fill(line, width=88, replace_whitespace=False)
            for line in txt.splitlines()
        )

        return (
            f"**Status update ({timestamp}):**\n\n"
            f"---\n"
            f"```text\n{wrapped}\n```\n"
            f"---\n"
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
