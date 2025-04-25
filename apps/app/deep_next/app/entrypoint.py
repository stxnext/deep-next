import json
import time
from datetime import datetime
from pathlib import Path

from deep_next.app.add_new_project import GitLabProjectConfig
from deep_next.app.config import (
    CONFIGS_DIR,
    FEATURE_BRANCH_NAME_TMPL,
    REPOSITORIES_DIR,
    DeepNextState,
)
from deep_next.app.git import FeatureBranch, GitRepository, setup_local_git_repo
from deep_next.connectors.aws import AWSSecretsManager
from deep_next.connectors.gitlab_connector import GitLabConnector, GitLabIssue
from deep_next.core.graph import (
    deep_next_action_plan_graph,
    deep_next_graph,
    deep_next_implement_graph,
)
from deep_next.core.io import write_txt
from deep_next.core.steps.action_plan.data_model import ActionPlan
from loguru import logger

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

def create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def find_issues(
    gitlab_connector: GitLabConnector, label: DeepNextState
) -> list[GitLabIssue]:
    """Fetches all issues to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [
        DeepNextState.IN_PROGRESS.name,
        DeepNextState.SOLVED.name,
        DeepNextState.FAILED.name,
    ]

    resp = []
    for issue in gitlab_connector.list_issues(label=label.name):
        if excluded := sorted([x for x in excluding_labels if x in issue.labels]):
            logger.warning(
                f"Skipping issue #{issue.no} ({issue.url}) due to label(s): {excluded}"
            )
            continue
        resp.append(issue)

    return resp


def get_projects_configs(configs_dir: Path = CONFIGS_DIR) -> list[GitLabProjectConfig]:
    """Loads all registered projects configurations."""
    configs: list[GitLabProjectConfig] = [
        GitLabProjectConfig.load(config_path)
        for config_path in configs_dir.iterdir()
        if config_path.suffix == ".json"
    ]

    return sorted(configs, key=lambda x: x.project_name) if configs else []


def _solve_issue(
    gitlab_project: GitLabConnector,
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
    ref_branch: str = "develop",
):
    """Solves a single issue."""
    feature_branch: FeatureBranch = local_repo.new_feature_branch(
        ref_branch,
        feature_branch=create_feature_branch_name(gitlab_issue.no),
    )
    gitlab_issue.add_comment(f"Assigned feature branch: `{feature_branch.name}`")

    start_time = time.time()
    try:
        _ = deep_next_graph(
            problem_statement=gitlab_issue,
            hints=gitlab_issue.comments,
            root=local_repo.repo_dir,
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        gitlab_issue.add_comment(msg)

    feature_branch.commit_all(commit_msg=f"DeepNext resolves #{gitlab_issue.no}")
    feature_branch.push_to_remote()

    mr = gitlab_project.create_mr(
        merge_branch=feature_branch.name,
        into_branch=ref_branch,
        title=f"Resolve '{gitlab_issue.title}'",
    )

    return mr


def _solve_issue_and_label(
    gitlab_project: GitLabConnector,
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
    ref_branch: str = "develop",
) -> bool:
    succeeded: bool

    try:
        gitlab_issue.add_label(DeepNextState.IN_PROGRESS)

        mr = _solve_issue(
            gitlab_project,
            gitlab_issue,
            local_repo,
            ref_branch=ref_branch,
        )
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for #{gitlab_issue.no}"
        logger.error(err_msg)
        gitlab_issue.add_comment(
            comment=err_msg, file_content=str(e), file_name="error_message.txt"
        )

        succeeded = False
        gitlab_issue.add_label(DeepNextState.FAILED)
    else:
        msg = f"🟢 Issue #{gitlab_issue.no} solved: {mr.web_url}"
        logger.success(msg)
        gitlab_issue.add_comment(msg)

        succeeded = True
        gitlab_issue.add_label(DeepNextState.SOLVED)
    finally:
        gitlab_issue.remove_label(DeepNextState.IN_PROGRESS)

    return succeeded


def _propose_action_plan(
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
) -> None:
    """Propose an action plan."""

    start_time = time.time()
    try:
        action_plan = deep_next_action_plan_graph(
            problem_statement=gitlab_issue.title + "\n" + gitlab_issue.description,
            hints=gitlab_issue.comments,
            root=local_repo.repo_dir,
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        gitlab_issue.add_comment(msg)

    gitlab_issue.add_comment(f"{ACTION_PLAN_PREFIX}{action_plan.model_dump()}")
    gitlab_issue.add_comment(f"{ACTION_PLAN_RESPONSE_INSTRUCTIONS}")


def _propose_action_plan_and_label(
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
) -> bool:
    succeeded: bool

    try:
        gitlab_issue.add_label(DeepNextState.IN_PROGRESS)

        _propose_action_plan(
            gitlab_issue,
            local_repo,
        )
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for #{gitlab_issue.no}"
        logger.error(err_msg)
        gitlab_issue.add_comment(
            comment=err_msg, file_content=str(e), file_name="error_message.txt"
        )

        succeeded = False
        gitlab_issue.add_label(DeepNextState.FAILED)
    else:
        succeeded = True
        gitlab_issue.add_label(DeepNextState.AWAITING_RESPONSE)
    finally:
        gitlab_issue.remove_label(DeepNextState.IN_PROGRESS)

    return succeeded


def _handle_user_action_plan_response_and_label(
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
):

    last_comment = gitlab_issue.comments[-1]


def _implement_action_plan(
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
):
    """Implements the action plan."""

    action_plan_json = None
    for comment in gitlab_issue.comments[::-1]:
        if comment.startswith(ACTION_PLAN_PREFIX):
            action_plan_json = comment[len(ACTION_PLAN_PREFIX) :].strip()
            break

    if not action_plan_json:
        logger.error("No action plan found in the issue comments.")
        return

    action_plan = ActionPlan.model_validate(json.loads(action_plan_json))

    start_time = time.time()
    try:
        git_diff = deep_next_implement_graph(
            action_plan=action_plan,
            root_dir=local_repo.repo_dir,
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        gitlab_issue.add_comment(msg)

    write_txt(txt=git_diff, path=local_repo.repo_dir / "result.diff")
    gitlab_issue.add_comment(f"# Result:\n{git_diff}")
    gitlab_issue.add_comment(
        f"# Result saved to: {local_repo.repo_dir / 'result.diff'}"
    )


def handle_project_issues(config: GitLabProjectConfig) -> None:
    """Solves all issues dedicated for DeepNext for a given project."""
    logger.debug(f"Creating gitlab connector for '{config.project_name}' project")
    gitlab_project = GitLabConnector(
        access_token=AWSSecretsManager().get_secret(config.gitlab.access_token),
        project_id=config.gitlab.project_id,
        base_url=config.gitlab.base_url,
    )

    logger.debug(f"Preparing local git repo for '{config.project_name}' project")
    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / config.project_name,
        ssh_url=config.git.repo_url,
    )

    results = []

    todo_e2e = find_issues(gitlab_project, DeepNextState.PENDING_E2E)
    for gitlab_issue in todo_e2e:
        succeeded = _solve_issue_and_label(
            gitlab_project,
            gitlab_issue,
            local_repo,
            ref_branch=config.git.ref_branch,
        )
        results.append(succeeded)

    todo_ap = find_issues(gitlab_project, DeepNextState.PENDING_AP)
    for gitlab_issue in todo_ap:
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

    # --------

    logger.debug(f"Looking for issues to be solved in '{config.project_name}' project")
    if not (todo := find_issues(gitlab_project)):
        logger.info(f"No issues to be solved for '{config.project_name}' repo")
        return

    logger.success(
        f"Found {len(todo)} issue(s) todo for '{config.project_name}' repo: "
        f"{sorted(f'#{issue.no}' for issue in todo)}"
    )

    failure = []
    success = []
    for gitlab_issue in todo:
        _solve_issue_and_label(
            gitlab_project,
            gitlab_issue,
            local_repo,
            ref_branch=config.git.ref_branch,
        )

    logger.success(
        f"Project '{config.project_name}' summary: "
        f"total={len(todo)}; solved={len(success)}; failed={len(failure)}"
    )


def main(configs_dir: Path = CONFIGS_DIR) -> None:
    """Solves issues dedicated for DeepNext for all registered projects."""
    logger.debug(f"Configs dir: '{configs_dir}'")

    if not (projects_registry := get_projects_configs(configs_dir)):
        logger.warning("No projects found. Register projects first.")
    else:
        logger.success(
            f"Found {len(projects_registry)} registered project(s): "
            f"{[config.project_name for config in projects_registry]}"
        )

        for config in projects_registry:
            logger.info(f"Resolving issues for '{config.project_name}' project...")
            handle_project_issues(config)

    logger.success("DeepNext app run completed.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
