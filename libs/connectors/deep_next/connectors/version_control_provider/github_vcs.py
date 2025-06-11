import re
from collections import defaultdict
from enum import Enum
from typing import List

from deep_next.app.common import format_comment_with_header
from deep_next.app.config import Label
from deep_next.connectors.version_control_provider.base import (
    BaseComment,
    BaseConnector,
    BaseIssue,
    BaseMR,
    CodeReviewCommentThread,
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
    def __init__(self, pr: PullRequest, related_issue: GitHubIssue):
        self._pr = pr
        self._related_issue = related_issue

    @property
    def related_issue(self) -> GitHubIssue:
        """Returns the related issue if exists."""
        return self._related_issue

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

    @property
    def labels(self) -> list[str]:
        """Returns the labels of the MR."""
        return [label.name for label in self._pr.get_labels()]

    @property
    def comments(self) -> list[GitHubComment]:
        """Returns the comments of the MR."""
        return [GitHubComment(comment) for comment in self._pr.get_issue_comments()]

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

    def add_label(self, label: str | Label):
        """Add a label to the MR."""
        label = label_to_str(label)
        self._pr.add_to_labels(label)

    def remove_label(self, label: str | Label):
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

    def reply_to_comment_thread(
        self, thread: CodeReviewCommentThread, body: str
    ) -> None:
        """Reply to a comment thread in the pull request."""
        self._pr.create_review_comment_reply(body=body, comment_id=thread.thread_id)

    def extract_comment_threads(self) -> List[CodeReviewCommentThread]:
        """Extracts comment threads from a GitHub pull request."""
        threads = defaultdict(list)
        for comment in self._pr.get_review_comments():
            thread_id = comment.in_reply_to_id or comment.id
            threads[thread_id].append(comment)

        result: List[CodeReviewCommentThread] = []
        for comments in threads.values():
            comments.sort(key=lambda c: c.created_at)
            root = comments[0]

            code_lines = [
                line[1:].rstrip()
                for line in root.diff_hunk.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            ]

            result.append(
                CodeReviewCommentThread(
                    thread_id=root.id,
                    file_path=root.path,
                    code_lines="\n".join(code_lines),
                    comments=[c.body for c in comments],
                )
            )

        return result


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
                logger.warning(
                    f"Label '{label}' not found in repository '{self.repo.full_name}'."
                )
                return []
        else:
            issues = list(self.repo.get_issues(state="open"))

        return [GitHubIssue(i) for i in issues if not i.pull_request]

    def get_issue(self, issue_no: int) -> GitHubIssue:
        issue = self.repo.get_issue(number=issue_no)
        return GitHubIssue(issue)

    def _has_label(self, raw_mr: PullRequest, label: str) -> bool:
        """Check if the MR has a specific label."""
        labels = [label.name for label in raw_mr.labels]
        return label in labels

    def list_mrs(self, label: str | Label | None = None) -> list[GitHubMR]:
        """Fetches all MRs"""
        prs = list(self.repo.get_pulls(state="open"))

        if label:
            if isinstance(label, Enum):
                label = label.value
            prs = [pr for pr in prs if self._has_label(pr, label)]

        return [
            GitHubMR(
                pr,
                related_issue=self.get_issue(
                    issue_no=self._extract_issue_number(pr.title)
                ),
            )
            for pr in prs
        ]

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
        draft=False,
    ) -> GitHubMR:
        pr = self.repo.create_pull(
            title=title,
            head=merge_branch,
            base=into_branch,
            body=description,
            draft=draft,
        )

        return GitHubMR(pr, related_issue=issue)

    # TODO: Connect with tile creator
    @staticmethod
    def _extract_issue_number(text: str) -> int:
        """Extracts the issue number from a given text."""
        match = re.search(r"issue\s+#(\d+)", text, re.IGNORECASE)

        if match:
            return int(match.group(1))

        raise ValueError(f"Could not extract issue number from text: '{text}'")
