import time
from datetime import datetime

from deep_next.app.config import (
    FEATURE_BRANCH_NAME_TMPL,
    REF_BRANCH,
    REPOSITORIES_DIR,
    DeepNextState,
)
from deep_next.app.git import FeatureBranch, GitRepository, setup_local_git_repo
from deep_next.app.vcs_config import VCSConfig, load_vcs_config_from_env
from deep_next.connectors.version_control_provider import (
    BaseConnector,
    BaseIssue,
    GitHubConnector,
    GitLabConnector, BaseMR,
)
from loguru import logger

from deep_next.core.graph import deep_next_graph, deep_next_action_plan_graph

ACTION_PLAN_PREFIX = "# Action Plan:\n"
ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "To access the action plan, respond with:"
    "\n```"
    "\n@deepnext"
    "\nOK"
    "\n```"
    "\n"
    "\nTo request changes to the action plan, specify the changes you want to see by using the following message format:"
    "\n```"
    "\n@deepnext"
    "\n<message to deepnext>"
    "\n```"
)


def _create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def find_issues(
    vcs_connector: BaseConnector, label: DeepNextState
) -> list[BaseIssue]:
    """Fetches all issues to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [DeepNextState.FAILED.name, DeepNextState.SOLVED, DeepNextState.IN_PROGRESS]

    resp = []
    for issue in vcs_connector.list_issues(label=label.name):
        if excluded := sorted([x for x in excluding_labels if x in issue.labels]):
            logger.warning(
                f"Skipping issue #{issue.no} ({issue.url}) due to label(s): {excluded}"
            )
            continue
        resp.append(issue)

    return resp


def _solve_issue(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str = REF_BRANCH,
) -> BaseMR | None:
    """Solves a single issue."""
    feature_branch: FeatureBranch = local_repo.new_feature_branch(
        ref_branch,
        feature_branch=_create_feature_branch_name(issue.no),
    )
    issue.add_comment(f"Assigned feature branch: `{feature_branch.name}`")

    start_time = time.time()
    try:
        deep_next_graph(
            problem_statement=issue.title + "\n" + issue.description,
            hints=issue.comments,
            root=local_repo.repo_dir
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        issue.add_comment(msg)

    feature_branch.commit_all(
        commit_msg=f"DeepNext resolves #{issue.no}: {issue.title}"
    )
    feature_branch.push_to_remote()

    mr = vcs_config.create_mr(
        merge_branch=feature_branch.name,
        into_branch=ref_branch,
        title=f"Resolve '{issue.title}'",
    )

    return mr


def _solve_issue_and_label(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str = REF_BRANCH,
) -> bool:
    success: bool
    try:
        issue.add_label(DeepNextState.IN_PROGRESS)

        mr = _solve_issue(
            vcs_config,
            issue,
            local_repo,
            ref_branch=ref_branch,
        )
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for #{issue.no}: {str(e)}"
        logger.error(err_msg)

        issue.add_label(DeepNextState.FAILED)
        issue.add_comment(
            comment=err_msg, file_content=str(e), file_name="error_message.txt"
        )

        success = False
    else:
        msg = f"🟢 Issue #{issue.no} solved: {mr.url}"
        logger.success(msg)

        issue.add_label(DeepNextState.SOLVED)
        issue.add_comment(msg)

        success = True
    finally:
        issue.remove_label(DeepNextState.IN_PROGRESS)

    return success


def _propose_action_plan(
    issue: BaseIssue,
    local_repo: GitRepository,
) -> None:
    """Propose an action plan."""

    start_time = time.time()
    try:
        action_plan = deep_next_action_plan_graph(
            problem_statement=issue.title + "\n" + issue.description,
            hints=issue.comments,
            root=local_repo.repo_dir,
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        issue.add_comment(msg)

    issue.add_comment(f"{ACTION_PLAN_PREFIX}{action_plan.model_dump()}")
    issue.add_comment(f"{ACTION_PLAN_RESPONSE_INSTRUCTIONS}")


def _propose_action_plan_and_label(
    issue: BaseIssue,
    local_repo: GitRepository,
) -> bool:
    succeeded: bool

    try:
        issue.add_label(DeepNextState.IN_PROGRESS)

        _propose_action_plan(
            issue,
            local_repo,
        )
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for #{issue.no}"
        logger.error(err_msg)
        issue.add_comment(
            comment=err_msg, file_content=str(e), file_name="error_message.txt"
        )

        succeeded = False
        issue.add_label(DeepNextState.FAILED)
    else:
        succeeded = True
        issue.add_label(DeepNextState.AWAITING_RESPONSE)
    finally:
        issue.remove_label(DeepNextState.IN_PROGRESS)

    return succeeded


def _handle_user_action_plan_response_and_label(
    issue: BaseIssue,
    local_repo: GitRepository,
) -> bool:

    last_comment = issue.comments[-1]


def _get_connector(config: VCSConfig) -> BaseConnector:
    """Creates a connector for the given project configuration."""
    if config.vcs == "github":
        return GitHubConnector(
            token=config.access_token,
            repo_name=config.repo_path,  # TODO: Fix naming
        )
    elif config.vcs == "gitlab":
        return GitLabConnector(
            access_token=config.access_token,
            repo_name=config.repo_path,
            base_url=config.base_url,
        )
    else:
        raise ValueError(
            f"Unsupported VCS, can't find related connector: '{config.vcs}'"
        )


def solve_project_issues(vcs_config: VCSConfig) -> None:
    """Solves all issues dedicated for DeepNext for a given project."""
    logger.debug(f"Creating connector for '{vcs_config.repo_path}' project")
    vcs_connector = _get_connector(vcs_config)

    logger.debug(f"Preparing local git repo for '{vcs_config.repo_path}' project")
    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )

    logger.debug(f"Looking for issues to handle in '{vcs_config.repo_path}' project")

    results = []
    for issue in find_issues(vcs_connector, label=DeepNextState.PENDING_E2E):
        logger.success(f"Found an issue for '{vcs_config.repo_path}' repo: #{issue.no}")
        success = _solve_issue_and_label(vcs_config, issue, local_repo, ref_branch=REF_BRANCH)
        results.append(success)

    for gitlab_issue in find_issues(vcs_connector, label=DeepNextState.PENDING_AP):
        if gitlab_issue.has_label(DeepNextState.AWAITING_RESPONSE):
            succeeded = _handle_user_action_plan_response_and_label(
                gitlab_issue,
                local_repo,
            )
            results.append(succeeded)
        else:
            succeeded = _propose_action_plan_and_label(
                gitlab_issue,
                local_repo,
            )
            results.append(succeeded)

    logger.success(
        f"Project '{vcs_config.repo_path}' summary: "
        f"total={len(results)}; solved={sum(results)}; failed={len(results) - sum(results)}"
    )


def main() -> None:
    """Solves issues dedicated for DeepNext for given project."""
    vcs_config: VCSConfig = load_vcs_config_from_env()

    logger.info(f"Looking for issues in '{vcs_config.repo_path}' project...")
    solve_project_issues(vcs_config)

    logger.success("DeepNext app run completed.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
