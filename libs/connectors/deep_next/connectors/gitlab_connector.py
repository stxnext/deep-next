import textwrap
from datetime import datetime

import gitlab
from gitlab.v4.objects.discussions import ProjectIssueDiscussion
from gitlab.v4.objects.issues import ProjectIssue
from gitlab.v4.objects.merge_requests import ProjectMergeRequest
from loguru import logger


class GitLabConnectorError(Exception):
    """Generic GitLab connector error."""


class ResourceNotFoundError(GitLabConnectorError):
    """Resource not found error."""


def filter_issues_by_label(issues, label):
    """Filter issues by label."""
    return [issue for issue in issues if label in issue.labels]


class GitLabIssue:
    def __init__(self, issue: ProjectIssue):
        self._issue = issue

        self.url = issue.web_url
        self.labels = issue.labels
        self.no = issue.iid
        self.title = issue.title
        self.description = issue.description

        self._discussion: ProjectIssueDiscussion | None = None
        self._comment_prefix = "[DeepNext]"

    @property
    def comments(self) -> str:
        """Get all issue comments except the ones added by DeepNext."""
        # TODO: Implement comments support. For now it's redundant - all in description
        return "<No comments>"

    def add_comment(
        self, comment: str, file_content: str | None = None, file_name="content.txt"
    ) -> None:
        # TODO: Tight coupling with GitLab API. It's pure deep_next.app logic.
        if self._discussion is None:
            top_lvl_comment = (
                f"## 🚧 DeepNext WIP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            )
            self._discussion = self._issue.discussions.create({"body": top_lvl_comment})

        def prettify_comment(txt: str) -> str:
            tmpl = textwrap.dedent(
                """\
            **Status update:**

            > {comment}
            """
            )

            return tmpl.format(comment=txt)

        self._discussion.notes.create({"body": prettify_comment(comment)})
        if file_content:
            self._add_file_attachment(file_name, file_content)

    def _add_file_attachment(self, filename: str, content: str) -> str:
        """
        Upload a text file and attach it to the issue.

        Args:
            filename: The name of the file to be uploaded
            content: The text content of the file

        Returns:
            The markdown representation of the uploaded file
        """
        project_id = self._issue.project_id
        gl = self._issue.manager.gitlab
        project = gl.projects.get(project_id)

        uploaded_file = project.upload(filename, filedata=content)

        comment = f"Attached file: {uploaded_file['markdown']}"
        self.add_comment(comment)

        return uploaded_file["markdown"]

    def has_label(self, label: str) -> bool:
        return label in self.labels

    def add_label(self, label: str) -> None:
        self._issue.labels.append(label)
        self._issue.save()

    def remove_label(self, label: str) -> None:
        if label not in self._issue.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return

        self._issue.labels = [x for x in self._issue.labels if x != label]
        self._issue.save()


class GitLabMR:
    def __init__(self, mr: ProjectMergeRequest):
        self._mr = mr

        self.url = mr.web_url
        self.no = mr.iid
        self.title = mr.title
        self.description = mr.description

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


class GitLabConnector:
    def __init__(self, *_, access_token: str, project_id: int, base_url: str):
        """Create connection with GitLab project."""
        self.project_id = project_id

        self.connector = gitlab.Gitlab(base_url, private_token=access_token)
        self.project = self.connector.projects.get(self.project_id)

    def list_issues(self, label=None) -> list[GitLabIssue]:
        """Fetches all issues"""
        all_issues = self.project.issues.list(all=True)
        issues = filter_issues_by_label(all_issues, label) if label else all_issues

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

    def get_mr(self, mr_no: int) -> GitLabMR:
        """Fetches a single merge request."""
        try:
            mr: ProjectMergeRequest = self.project.mergerequests.get(mr_no)
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ResourceNotFoundError(f"MR #{mr_no} not found.") from None
            else:
                raise GitLabConnectorError(
                    f"Error while fetching MR #{mr_no}: {e}"
                ) from None

        return GitLabMR(mr)

    def create_mr(
        self,
        merge_branch: str,
        into_branch: str,
        title: str,
    ):
        """Create merge request."""
        logger.info(f"Creating MR from '{merge_branch}' to '{into_branch}'")

        return self.project.mergerequests.create(
            {
                "source_branch": merge_branch,
                "target_branch": into_branch,
                "title": title,
                "labels": [],
            }
        )
