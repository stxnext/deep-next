import gitlab
from deep_next.connectors.version_control_provider.base import (
    BaseConnector,
    BaseIssue,
    BaseMR,
)
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
    def comments(self) -> str:
        """Get all issue comments except the ones added by DeepNext."""
        return "<No comments>"

    def add_comment(
        self, comment: str, file_content: str | None = None, file_name="content.txt"
    ) -> None:
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

    def add_label(self, label: str) -> None:
        self._issue.labels.append(label)
        self._issue.save()

    def remove_label(self, label: str) -> None:
        if label not in self._issue.labels:
            logger.warning(f"Label '{label}' not found in issue #{self.no}")
            return

        self._issue.labels = [x for x in self._issue.labels if x != label]
        self._issue.save()


class GitLabMR(BaseMR):
    def __init__(self, mr: ProjectMergeRequest):
        self._mr = mr

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

    def post_action_plan_comment(self, reasoning: str, steps: list[str]) -> None:
        """Post reasoning and steps as a comment in the MR."""
        comment_body = self._format_action_plan_comment(reasoning, steps)
        self._mr.notes.create({"body": comment_body})

    @staticmethod
    def _format_action_plan_comment(reasoning: str, steps: list[str]) -> str:
        """Format the action plan comment for MR."""
        formatted_steps = "\n".join(f"- {step}" for step in steps)
        return (
            "### 🤖 DeepNext Action Plan\n\n"
            f"**Reasoning:**\n{reasoning}\n\n"
            f"**Steps:**\n{formatted_steps}"
        )


class GitLabConnector(BaseConnector):
    def __init__(self, *_, access_token: str, repo_name: str, base_url: str):
        """Create connection with GitLab project."""
        self.repo_name = repo_name

        self.connector = gitlab.Gitlab(base_url, private_token=access_token)
        self.project = self.connector.projects.get(self.repo_name)

        self.project_id = self.project.id

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

    def post_action_plan_to_mr(
        self, mr_no: int, reasoning: str, steps: list[str]
    ) -> None:
        """Post reasoning and steps as a comment to the MR."""
        mr = self.get_mr(mr_no)
        mr.post_action_plan_comment(reasoning, steps)

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
