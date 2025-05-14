from enum import Enum

import gitlab
from deep_next.app.common import format_comment_with_header
from deep_next.app.config import DeepNextLabel
from deep_next.connectors.version_control_provider.base import (
    BaseComment,
    BaseConnector,
    BaseIssue,
    BaseMR,
)
from deep_next.connectors.version_control_provider.utils import label_to_str
from gitlab.v4.objects.discussions import ProjectIssueDiscussion
from gitlab.v4.objects.issues import ProjectIssue
from gitlab.v4.objects.merge_requests import ProjectMergeRequest
from loguru import logger


class GitLabConnectorError(Exception):
    """Generic GitLab connector error."""


class ResourceNotFoundError(GitLabConnectorError):
    """Resource not found error."""


def filter_by_label(issues_or_mrs: list, label: str) -> list:
    """Filter issues or labels by label."""
    return [issue_or_mr for issue_or_mr in issues_or_mrs if label in issue_or_mr.labels]


class GitLabComment(BaseComment):
    def __init__(self, comment: ProjectIssueDiscussion):
        self._comment = comment

    @property
    def body(self) -> str:
        return self._comment.body.replace("\r\n", "\n")

    def edit(self, body: str) -> None:
        self._comment.update(body=body)

    @property
    def author(self) -> str:
        return self._comment.author["name"]


class GitLabIssue(BaseIssue):
    def __init__(self, issue: ProjectIssue):
        self._issue = issue
        self._discussion: ProjectIssueDiscussion | None = None

    @property
    def url(self) -> str:
        return self._issue.web_url

    @property
    def labels(self) -> list[str]:
        return self._issue.labels

    @property
    def no(self) -> int:
        return self._issue.iid

    @property
    def title(self) -> str:
        return self._issue.title

    @property
    def description(self) -> str:
        return self._issue.description

    @property
    def comments(self) -> list:
        """Get all issue comments except the ones added by DeepNext."""
        return ["<No comments>"]

    def add_comment(
        self,
        comment: str,
        file_content: str | None = None,
        info_header: bool = False,
        file_name="content.txt",
    ) -> None:
        if info_header:
            comment = format_comment_with_header(comment)

        if self._discussion is None:
            self._discussion = self._issue.discussions.create(
                {"body": self.comment_thread_header}
            )

        self._discussion.notes.create({"body": self.prettify_comment(comment)})

        if file_content:
            self._add_file_attachment(file_name, file_content)

    def _add_file_attachment(self, filename: str, content: str) -> str:
        """Upload a text file and attach it to the issue."""
        project_id = self._issue.project_id
        gl = self._issue.manager.gitlab

        project = gl.projects.get(project_id)

        uploaded_file = project.upload(filename, filedata=content)

        comment = f"Attached file: {uploaded_file['markdown']}"
        self.add_comment(comment)

        return uploaded_file["markdown"]

    def add_label(self, label: str | Enum) -> None:
        self._issue.labels.append(label_to_str(label))
        self._issue.save()

    def remove_label(self, label: str | Enum) -> None:
        label = label_to_str(label)
        if label not in self._issue.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return

        self._issue.labels = [x for x in self._issue.labels if x != label]
        self._issue.save()


class GitLabMR(BaseMR):
    def __init__(self, mr: ProjectMergeRequest):
        self._mr = mr

    @property
    def source_branch_name(self) -> str:
        return self._mr.source_branch

    @property
    def target_branch_name(self) -> str:
        return self._mr.target_branch

    @property
    def url(self) -> str:
        return self._mr.web_url

    @property
    def no(self) -> int:
        return self._mr.iid

    @property
    def title(self) -> str:
        return self._mr.title

    @property
    def description(self) -> str:
        return self._mr.description

    @property
    def base_commit(self) -> str:
        """Base commit for MR (the one on which changes are applied)."""
        return self._mr.diff_refs["start_sha"]

    def git_diff(self) -> str:
        """Retrieve the full git diff for a given merge request."""
        diffs = self._mr.changes()["changes"]

        diff_output = []
        for change in diffs:
            before_filepath = change["old_path"]
            after_filepath = change["new_path"]

            if before_filepath != after_filepath:
                diff_output.append(f"rename from {before_filepath}")
                diff_output.append(f"rename to {after_filepath}")
            else:
                diff_output.append(f"diff --git a/{before_filepath} b/{after_filepath}")

            diff_output.append(f"--- a/{before_filepath}")
            diff_output.append(f"+++ b/{after_filepath}")

            diff_output.append(change["diff"])

        return "\n".join(diff_output)

    @property
    def labels(self) -> list[str]:
        """Returns the labels of the MR."""
        return self._mr.labels

    def add_label(self, label: str | DeepNextLabel):
        """Add a label to the MR."""
        label = label_to_str(label)
        # TODO: Replace with the proper implementation.
        self._mr.add_to_labels(label)

    def remove_label(self, label: str | DeepNextLabel):
        """Remove a label from the MR."""
        label = label_to_str(label)
        # TODO: Replace with the proper implementation.
        self._mr.remove_from_labels(label)

    def add_comment(
        self,
        comment: str,
        info_header: bool = False,
        log: int | str | None = None
    ) -> None:
        """Adds a comment to the MR."""
        if info_header:
            comment = format_comment_with_header(comment)

        if log is not None:
            logger.log(log, comment)

        self._mr.notes.create({"body": comment})

    @property
    def comments(self) -> list[BaseComment]:
        """Returns the comments of the MR."""
        # TODO: Replace with the proper implementation.
        return [GitLabComment(comment) for comment in self._mr.notes.list()]


class GitLabConnector(BaseConnector):
    def __init__(self, *_, access_token: str, repo_name: str, base_url: str):
        """Create connection with GitLab project."""
        self.repo_name = repo_name

        self.connector = gitlab.Gitlab(base_url, private_token=access_token)
        self.project = self.connector.projects.get(self.repo_name)

        self.project_id = self.project.id

    def list_issues(self, label: str | Enum | None = None) -> list[GitLabIssue]:
        """Fetches all issues"""
        label = label_to_str(label)
        all_issues = self.project.issues.list(all=True)
        issues = filter_by_label(all_issues, label) if label else all_issues

        return [GitLabIssue(issue) for issue in issues]

    def get_issue(self, issue_no: int) -> GitLabIssue:
        """Fetches a single issue."""
        try:
            issue: ProjectIssue = self.project.issues.get(issue_no)
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ResourceNotFoundError(f"Issue #{issue_no} not found.") from None
            else:
                raise GitLabConnectorError(
                    f"Error while fetching issue #{issue_no}: {e}"
                ) from None

        return GitLabIssue(issue)

    def list_mrs(self, label: str | None = None) -> list[GitLabMR]:
        """Fetches all MRs"""
        all_mrs = self.project.mergerequests.list(all=True)
        mrs = filter_by_label(all_mrs, label) if label else all_mrs

        return [GitLabMR(mr) for mr in mrs]

    def get_mr(self, mr_no: int) -> GitLabMR:
        """Fetches a single merge request."""
        try:
            mr: ProjectMergeRequest = self.project.mergerequests.get(mr_no)
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ResourceNotFoundError(f"MR #{mr_no} not found.") from e
            else:
                raise GitLabConnectorError(
                    f"Error while fetching MR #{mr_no}: {e}"
                ) from e

        return GitLabMR(mr)

    def create_mr(
        self,
        merge_branch: str,
        into_branch: str,
        title: str,
        description: str | None = None,
        issue: GitLabIssue | None = None,
    ) -> GitLabMR:
        """Create merge request."""
        logger.info(f"Creating MR from '{merge_branch}' to '{into_branch}'")

        try:
            mr: ProjectMergeRequest = self.project.mergerequests.create(
                {
                    "source_branch": merge_branch,
                    "target_branch": into_branch,
                    "title": title,
                    "description": description,
                    "labels": [],
                }
            )
        except gitlab.exceptions.GitlabGetError as e:
            raise GitLabConnectorError(f"Error while creating MR: {e}") from e

        return GitLabMR(mr)
