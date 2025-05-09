import re
from enum import Enum
from typing import List

from deep_next.app.common import format_comment_with_header
from deep_next.app.config import DeepNextLabel
from deep_next.connectors.version_control_provider.base import (
    BaseComment,
    BaseConnector,
    BaseIssue,
    BaseMR,
)
from deep_next.connectors.version_control_provider.utils import label_to_str
from github import Github
from github.GithubException import UnknownObjectException
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository
from loguru import logger


class GitHubComment(BaseComment):
    def __init__(self, comment: IssueComment):
        self._comment = comment

    @property
    def body(self) -> str:
        return self._comment.body.replace("\r\n", "\n")

    def edit(self, body: str) -> None:
        self._comment.edit(body)

    @property
    def author(self) -> str:
        return self._comment.user.name


class GitHubIssue(BaseIssue):
    def __init__(self, issue: Issue):
        self._issue = issue
        self._anchor_comment: IssueComment | None = None

    @property
    def url(self) -> str:
        return self._issue.html_url

    @property
    def labels(self) -> list[str]:
        return [label.name for label in self._issue.get_labels()]

    @property
    def no(self) -> int:
        return self._issue.number

    @property
    def title(self) -> str:
        return self._issue.title

    @property
    def description(self) -> str:
        return self._issue.body or ""

    @property
    def comments(self) -> list[GitHubComment]:
        return [GitHubComment(comment) for comment in self._issue.get_comments()]

    def add_comment(
        self,
        comment: str,
        file_content: str | None = None,
        info_header: bool = False,
        file_name="content.txt",
    ) -> None:
        """Create or append to the DeepNext anchor comment."""
        if info_header:
            comment = format_comment_with_header(comment)

        self._create_comment(comment)

    def _create_comment(self, body: str) -> GitHubComment:
        """Create a new comment."""
        return GitHubComment(self._issue.create_comment(body))

    def add_label(self, label: str | Enum) -> None:
        label = label_to_str(label)
        if label not in self.labels:
            self._issue.add_to_labels(label)
            self.labels.append(label)

    def remove_label(self, label: str | Enum) -> None:
        label = label_to_str(label)
        if label not in self.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return

        self._issue.remove_from_labels(label)


class GitHubMR(BaseMR):
    def __init__(self, pr: PullRequest):
        self._pr = pr

    @property
    def source_branch_name(self) -> str:
        return self._pr.head.ref

    @property
    def target_branch_name(self) -> str:
        return self._pr.base.ref

    @property
    def url(self) -> str:
        return self._pr.html_url

    @property
    def no(self) -> int:
        return self._pr.number

    @property
    def title(self) -> str:
        return self._pr.title

    @property
    def description(self) -> str:
        return self._pr.body or ""

    @property
    def base_commit(self) -> str:
        """Base commit for PR (the one on which changes are applied)."""
        return self._pr.base.sha

    def git_diff(self) -> str:
        """Construct a full git diff from the files in the pull request."""
        diffs = []

        for file in self._pr.get_files():
            before = file.previous_filename or file.filename
            after = file.filename

            if file.status == "renamed":
                diffs.append(f"rename from {before}")
                diffs.append(f"rename to {after}")
            else:
                diffs.append(f"diff --git a/{before} b/{after}")

            diffs.append(f"--- a/{before}")
            diffs.append(f"+++ b/{after}")

            diffs.append(file.patch or "")

        return "\n".join(diffs)

    @property
    def labels(self) -> list[str]:
        """Returns the labels of the MR."""
        return [label.name for label in self._pr.get_labels()]

    def add_label(self, label: str | DeepNextLabel):
        """Add a label to the MR."""
        label = label_to_str(label)
        self._pr.add_to_labels(label)

    def remove_label(self, label: str | DeepNextLabel):
        """Remove a label from the MR."""
        label = label_to_str(label)
        self._pr.remove_from_labels(label)

    def add_comment(
        self, comment: str, info_header: bool = False, log: int | str | None = None
    ) -> None:
        """Adds a comment to the MR."""
        if info_header:
            comment = format_comment_with_header(comment)

        if log is not None:
            logger.log(log, comment)

        self._pr.create_issue_comment(comment)

    @property
    def comments(self) -> list[GitHubComment]:
        """Returns the comments of the MR."""
        return [GitHubComment(comment) for comment in self._pr.get_issue_comments()]


class GitHubConnector(BaseConnector):
    def __init__(self, *_, token: str, repo_name: str):
        self.github = Github(token)
        self.repo: Repository = self.github.get_repo(repo_name)

    def list_issues(self, label: str | Enum | None = None) -> List[GitHubIssue]:
        label = label_to_str(label)
        if label:
            try:
                issues = list(
                    self.repo.get_issues(
                        state="open", labels=[self.repo.get_label(label)]
                    )
                )
            except UnknownObjectException:
                # This means a 404 was returned, which means the label does not exist.
                return []
        else:
            issues = list(self.repo.get_issues(state="open"))

        # GitHub returns both issues and pull requests in the same list.
        issues = [
            issue for issue in issues if not re.search(r"pull/\d+$", issue.html_url)
        ]

        return [GitHubIssue(i) for i in issues]

    def get_issue(self, issue_no: int) -> GitHubIssue:
        issue = self.repo.get_issue(number=issue_no)
        return GitHubIssue(issue)

    def _has_label(self, raw_mr: PullRequest, label: str) -> bool:
        """Check if the MR has a specific label."""
        labels = [label.name for label in raw_mr.labels]
        return label in labels

    def list_mrs(self, label: str | None = None) -> list[GitHubMR]:
        """Fetches all MRs"""
        prs = list(self.repo.get_pulls(state="open"))

        if label:
            prs = [pr for pr in prs if self._has_label(pr, label)]

        return [GitHubMR(pr) for pr in prs]

    def get_mr(self, mr_no: int) -> GitHubMR:
        pr = self.repo.get_pull(number=mr_no)

        return GitHubMR(pr)

    def create_mr(
        self,
        merge_branch: str,
        into_branch: str,
        title: str,
        description: str | None = None,
        issue: GitHubIssue | None = None,
    ) -> GitHubMR:
        pr = self.repo.create_pull(
            title=title,
            head=merge_branch,
            base=into_branch,
            body=description,
        )
        return GitHubMR(pr)
