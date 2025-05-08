from loguru import logger

from deep_next.app.common import create_feature_branch_name, DEEP_NEXT_PR_DESCRIPTION
from deep_next.app.config import (
    REF_BRANCH,
    REPOSITORIES_DIR,
    DeepNextLabel,
)
from deep_next.app.git import GitRepository, setup_local_git_repo, FeatureBranch
from deep_next.app.handle_mr.e2e import handle_mr_e2e
from deep_next.app.handle_mr.hitl import handle_mr_human_in_the_loop
from deep_next.app.utils import get_connector
from deep_next.app.vcs_config import VCSConfig, load_vcs_config_from_env
from deep_next.connectors.version_control_provider import (
    BaseConnector,
    BaseIssue,
    BaseMR,
)

MESSAGE_TO_DEEPNEXT_PREFIX = "@deepnext"

ACTION_PLAN_PREFIX = "## Action Plan"
ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\nTo ACCEPT the action plan, respond with:"
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\nOK"
    "\n```"
    "\n"
    "\nTo REQUEST CHANGES to the action plan, talk to DeepNext using the following message format:"  # noqa: E501
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\n*<message to deepnext>*"
    "\n```"
)


def create_mr_and_comment(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str,
    deep_next_state: DeepNextLabel,
):
    """Create an MR/PR to solve an issue and link the MR/PR in an issue's comment."""
    try:
        issue.remove_label(deep_next_state)

        feature_branch: FeatureBranch = local_repo.new_feature_branch(
            ref_branch,
            feature_branch=create_feature_branch_name(issue.no),
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


def find_mrs(vcs_connector: BaseConnector, label: DeepNextLabel) -> list[BaseMR]:
    """Fetches all merge requests to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [
        DeepNextLabel.FAILED.value,
        DeepNextLabel.SOLVED.value,
        DeepNextLabel.IN_PROGRESS.value,
    ]

    resp = []
    for mr in vcs_connector.list_mrs(label=label.value):
        if excluded := sorted([x for x in excluding_labels if x in mr.labels]):
            logger.warning(
                f"Skipping MR #{mr.no} ({mr.url}) due to label(s): {excluded}"
            )
            continue
        resp.append(mr)

    return resp


def _get_last_action_plan(issue: BaseIssue) -> str | None:
    for comment in issue.comments[::-1]:
        if comment.body.startswith(ACTION_PLAN_PREFIX):
            action_plan = comment.body[len(ACTION_PLAN_PREFIX) :].strip()
            return action_plan
    return None


def handle_issues(vcs_config: VCSConfig) -> None:
    vcs_connector = get_connector(vcs_config)

    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )


    for issue in vcs_connector.list_issues(label=DeepNextLabel.PENDING_E2E):
        create_mr_and_comment(
            vcs_config,
            issue,
            local_repo,
            ref_branch=REF_BRANCH,
            deep_next_state=DeepNextLabel.PENDING_E2E,
        )

    for issue in vcs_connector.list_issues(label=DeepNextLabel.PENDING_HITL):
        create_mr_and_comment(
            vcs_config,
            issue,
            local_repo,
            ref_branch=REF_BRANCH,
            deep_next_state=DeepNextLabel.PENDING_HITL,
        )


def handle_mrs(vcs_config: VCSConfig) -> None:
    vcs_connector = get_connector(vcs_config)

    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )

    for mr in find_mrs(vcs_connector, label=DeepNextLabel.PENDING_E2E):
        handle_mr_e2e(
            mr,
            local_repo,
            vcs_connector,
        )

    for mr in find_mrs(vcs_connector, label=DeepNextLabel.PENDING_HITL):
        handle_mr_human_in_the_loop(
            mr,
            local_repo,
            vcs_connector,
        )


def main() -> None:
    """Solves issues dedicated for DeepNext for given project."""
    vcs_config: VCSConfig = load_vcs_config_from_env()

    handle_issues(vcs_config)
    handle_mrs(vcs_config)

    logger.success("DeepNext app run completed.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
