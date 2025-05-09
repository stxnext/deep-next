import textwrap
from typing import List

from deep_next.connectors.version_control_provider.base import (
    BaseConnector,
    BaseIssue,
    BaseMR,
)
from github import Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository
from loguru import logger


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
    def comments(self) -> str:
        return "<No comments>"

    def add_comment(
        self, comment: str, file_content: str | None = None, file_name="content.txt"
    ) -> None:
        """Create or append to the DeepNext anchor comment."""
        if self._anchor_comment is None:
            self._anchor_comment = self._get_or_create_anchor_comment()

        body = self.prettify_comment(comment)

        if file_content:
            gist_url = self._upload_gist(file_name, file_content)
            body += (
                f"\n\n**Attached file** [`{file_name}`]({gist_url})"
            )

        updated_body = f"{self._anchor_comment.body.rstrip()}\n\n---\n\n{body}"
        self._anchor_comment.edit(updated_body)

    def _get_or_create_anchor_comment(self) -> IssueComment:
        """Find existing DeepNext thread or create a new one."""
        for comment in self._issue.get_comments():
            if comment.body.startswith(self._comment_prefix):
                return comment

        anchor = self._issue.create_comment(self.comment_thread_header)

        return anchor

    @staticmethod
    def _format_file_attachment(filename: str, content: str) -> str:
        """Simulate file attachment using Markdown code block."""
        return textwrap.dedent(
            f"""\
            **Attached file** `{filename}`:
            ```text
            {content}
            ```
        """
        )

    def _upload_gist(self, file_name: str, file_content: str) -> str:
        """Upload file as a GitHub Gist and return the Gist file URL."""
        gist = self._issue._requester._Github__requester.github.get_user().create_gist(
            public=False,
            files={file_name: {"content": file_content}},
            description=f"Attachment for issue #{self.no}: {file_name}",
        )
        # Get the URL to the file in the Gist
        file_info = gist.files[file_name]
        return file_info.raw_url

    def add_label(self, label: str) -> None:
        if label not in self.labels:
            self._issue.add_to_labels(label)
            self.labels.append(label)

    def remove_label(self, label: str) -> None:
        if label not in self.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return

        self._issue.remove_from_labels(label)


class GitHubMR(BaseMR):
    def __init__(self, pr: PullRequest):
        self._pr = pr

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


class GitHubConnector(BaseConnector):
    def __init__(self, *_, token: str, repo_name: str):
        self.github = Github(token)
        self.repo: Repository = self.github.get_repo(repo_name)

    def list_issues(self, label: str | None = None) -> List[GitHubIssue]:
        if label:
            issues = list(
                self.repo.get_issues(state="all", labels=[self.repo.get_label(label)])
            )
        else:
            issues = list(self.repo.get_issues(state="all"))

        return [GitHubIssue(i) for i in issues]

    def get_issue(self, issue_no: int) -> GitHubIssue:
        issue = self.repo.get_issue(number=issue_no)
        return GitHubIssue(issue)

    def get_mr(self, mr_no: int) -> GitHubMR:
        pr = self.repo.get_pull(number=mr_no)

        return GitHubMR(pr)

    def create_mr(
        self,
        merge_branch: str,
        into_branch: str,
        title: str,
    ) -> GitHubMR:
        pr = self.repo.create_pull(
            title=title, head=merge_branch, base=into_branch, body=""
        )
        return GitHubMR(pr)
