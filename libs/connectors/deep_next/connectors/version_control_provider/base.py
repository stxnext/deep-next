from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

from deep_next.app.common import extract_issue_number_from_mr
from deep_next.app.config import DeepNextLabel
from deep_next.connectors.version_control_provider.utils import label_to_str


class BaseComment(ABC):
    @property
    @abstractmethod
    def body(self) -> str:
        """Returns the body of the comment."""

    @abstractmethod
    def edit(self, body: str) -> None:
        """Edit the comment."""

    @abstractmethod
    def author(self) -> str:
        """Returns the author of the comment."""


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
    def issue_statement(self) -> str:
        return self.title + "\n\n" + self.description

    @property
    @abstractmethod
    def comments(self) -> list[BaseComment]:
        """"""

    @abstractmethod
    def add_comment(
        self,
        comment: str,
        file_content: str | None = None,
        info_header: bool = False,
        file_name="content.txt",
    ) -> None:
        """"""

    @abstractmethod
    def add_label(self, label: str | Enum) -> None:
        """"""

    @abstractmethod
    def remove_label(self, label: str | Enum) -> None:
        """"""

    @property
    def _comment_prefix(self) -> str:
        return "[DeepNext]"

    @property
    def comment_thread_header(self):
        return f"## 🚧 DeepNext WIP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"

    def has_label(self, label: str | Enum) -> bool:
        return label_to_str(label) in self.labels

    @staticmethod
    def prettify_comment(txt: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"**Status update ({timestamp}):**" f"\n" f"\n{txt}"


class BaseMR(ABC):

    def issue(self, connector: 'BaseConnector') -> BaseIssue | None:
        """Returns the issue associated with the MR."""
        issue_no = extract_issue_number_from_mr(self)
        if issue_no is None:
            return None
        return connector.get_issue(issue_no)

    @property
    @abstractmethod
    def source_branch_name(self) -> str:
        """Returns the source branch of the MR."""

    @property
    @abstractmethod
    def target_branch_name(self) -> str:
        """Returns the target branch of the MR."""

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

    @property
    @abstractmethod
    def labels(self) -> list[str]:
        """Returns the labels of the MR."""

    @abstractmethod
    def add_label(self, label: str | DeepNextLabel):
        """Add a label to the MR."""

    @abstractmethod
    def remove_label(self, label: str | DeepNextLabel):
        """Remove a label from the MR."""

    @abstractmethod
    def add_comment(self, comment: str, info_header: bool = False, log: int | str | None = None) -> None:
        """Adds a comment to the MR."""

    @property
    @abstractmethod
    def comments(self) -> list[BaseComment]:
        """Returns the comments of the MR."""

class BaseConnector(ABC):
    @abstractmethod
    def list_issues(self, label: str | Enum | None = None) -> list[BaseIssue]:
        """Fetches all issues"""

    @abstractmethod
    def get_issue(self, issue_no: int) -> BaseIssue:
        """Fetches a single issue."""

    @abstractmethod
    def list_mrs(self, label: str | None = None) -> list[BaseIssue]:
        """Fetches all MRs"""

    @abstractmethod
    def get_mr(self, mr_no: int) -> BaseMR:
        """Fetches a single merge request."""

    @abstractmethod
    def create_mr(self, merge_branch: str, into_branch: str, title: str, issue: BaseIssue) -> BaseMR:
        """Creates new merge request."""
