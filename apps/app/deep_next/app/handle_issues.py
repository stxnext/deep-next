from datetime import datetime

from loguru import logger

from deep_next.app.common import DEEP_NEXT_PR_DESCRIPTION
from deep_next.app.config import (
    REF_BRANCH, DeepNextState, FEATURE_BRANCH_NAME_TMPL,
)
from deep_next.app.git import FeatureBranch, GitRepository
from deep_next.app.vcs_config import VCSConfig
from deep_next.connectors.version_control_provider import (
    BaseIssue,
)


def _create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def _create_mr_and_comment(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str,
    deep_next_state: DeepNextState = DeepNextState.PENDING_E2E,
):
    """Create an MR/PR to solve an issue and link the MR/PR in an issue's comment."""
    try:
        issue.remove_label(deep_next_state)

        feature_branch: FeatureBranch = local_repo.new_feature_branch(
            ref_branch,
            feature_branch=_create_feature_branch_name(issue.no),
        )

        change_id = feature_branch.make_temporary_change()
        feature_branch.commit_all("Temporary change - undo after MR is created.")
        feature_branch.push_to_remote()

        mr = vcs_config.create_mr(
            merge_branch=feature_branch.name,
            into_branch=ref_branch,
            title=f"Resolve '{issue.title}'",
            description=f"{DEEP_NEXT_PR_DESCRIPTION.format(issue_no=issue.no)}"
                        f"\n\nDo not modify this part of the description. You can add additional information below this line."
                        f"\n\n---\n\n",
            issue=issue,
        )

        feature_branch.remove_temporary_change(change_id)
        feature_branch.commit_all("Temporary change undone.")
        feature_branch.push_to_remote()

        mr.add_label(deep_next_state)

        message = (
            f"Assigned feature branch: `{feature_branch.name}`"
            f"\n"
            f"\n🟢 Issue #{issue.no} solution: {mr.url}"
        )

        issue.add_comment(message, info_header=True)
        logger.info(message)
    except Exception as e:
        message = f"🔴 Failed to create MR/PR:\n\n{e}"
        logger.info(message)
        issue.add_comment(message, info_header=True)


def handle_e2e(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str = REF_BRANCH,
):
    """Create an MR/PR to solve a single issue with no human input needed."""
    _create_mr_and_comment(
        vcs_config,
        issue,
        local_repo,
        ref_branch,
        deep_next_state=DeepNextState.PENDING_E2E,
    )


def handle_human_in_the_loop(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str = REF_BRANCH
):
    """Create an MR/PR to solve a single issue with human input needed."""
    _create_mr_and_comment(
        vcs_config,
        issue,
        local_repo,
        ref_branch,
        deep_next_state=DeepNextState.PENDING_HITL,
    )
