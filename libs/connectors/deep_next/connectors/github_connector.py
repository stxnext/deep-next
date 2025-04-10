import textwrap
from datetime import datetime
from typing import List

from github import Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository
from loguru import logger


class GitHubIssue:
    def __init__(self, issue: Issue):
        self._issue = issue

        self.url = issue.html_url
        self.labels = [label.name for label in issue.get_labels()]
        self.no = issue.number
        self.title = issue.title
        self.description = issue.body or ""

        self._anchor_comment: IssueComment | None = None
        self._comment_prefix = "[DeepNext]"

    @property
    def comments(self) -> str:
        """Get all issue comments except the ones added by DeepNext."""
        # TODO: Implement comments support. For now it's redundant - all in description
        return "<No comments>"

    def add_comment(
        self, comment: str, file_content: str | None = None, file_name="content.txt"
    ) -> None:
        """Create or append to the DeepNext anchor comment."""
        if self._anchor_comment is None:
            self._anchor_comment = self._get_or_create_anchor_comment()

        def prettify_comment(txt: str) -> str:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return textwrap.dedent(
                f"""\
                **Status update ({timestamp}):**

                > {txt}
            """
            )

        body = prettify_comment(comment)

        if file_content:
            body += f"\n\n{self._format_file_attachment(file_name, file_content)}"

        updated_body = f"{self._anchor_comment.body.rstrip()}\n\n---\n\n{body}"
        self._anchor_comment.edit(updated_body)

    def _get_or_create_anchor_comment(self) -> IssueComment:
        """Find existing DeepNext thread or create a new one."""
        for comment in self._issue.get_comments():
            if comment.body.startswith(self._comment_prefix):
                return comment

        header = (
            f"{self._comment_prefix} 🚧 DeepNext WIP "
            f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        )
        anchor = self._issue.create_comment(header)

        return anchor

    def _format_file_attachment(self, filename: str, content: str) -> str:
        """Simulate file attachment using markdown code block."""
        return textwrap.dedent(
            f"""\
            **Attached file** `{filename}`:
            ```text
            {content}
            ```
        """
        )

    def has_label(self, label: str) -> bool:
        return label in self.labels

    def add_label(self, label: str) -> None:
        if label not in self.labels:
            self._issue.add_to_labels(label)
            self.labels.append(label)

    def remove_label(self, label: str) -> None:
        if label not in self.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return
        self._issue.remove_from_labels(label)
        self.labels = [x for x in self.labels if x != label]


class GitHubMR:
    def __init__(self, pr: PullRequest):
        self._pr = pr

        self.url = pr.html_url
        self.no = pr.number
        self.title = pr.title
        self.description = pr.body or ""

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


class GitHubConnector:
    def __init__(self, token: str, repo_name: str):
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
    ) -> PullRequest:
        pr = self.repo.create_pull(
            title=title, head=merge_branch, base=into_branch, body=""
        )
        return pr
