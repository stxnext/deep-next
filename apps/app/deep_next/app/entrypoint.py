import time
from datetime import datetime

from deep_next.app.config import (
    FAILED_LABEL,
    FEATURE_BRANCH_NAME_TMPL,
    IN_PROGRESS_LABEL,
    REF_BRANCH,
    REPOSITORIES_DIR,
    SOLVED_LABEL,
    TODO_LABEL,
)
from deep_next.app.git import FeatureBranch, GitRepository, setup_local_git_repo
from deep_next.app.vcs_config import VCSConfig, load_vcs_config_from_env
from deep_next.connectors.version_control_provider import (
    BaseConnector,
    BaseIssue,
    GitHubConnector,
    GitLabConnector,
)
from deep_next.core.entrypoint import DeepNextResult
from deep_next.core.entrypoint import main as deep_next_pipeline
from loguru import logger


def _create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def find_issues(
    vcs_connector: BaseConnector, deep_next_label: str = TODO_LABEL
) -> list[BaseIssue]:
    """Fetches all issues to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [FAILED_LABEL, SOLVED_LABEL, IN_PROGRESS_LABEL]

    resp = []
    for issue in vcs_connector.list_issues(label=deep_next_label):
        if excluded := sorted([x for x in excluding_labels if x in issue.labels]):
            logger.warning(
                f"Skipping issue #{issue.no} ({issue.url}) due to label(s): {excluded}"
            )
            continue
        resp.append(issue)

    return resp


def solve_issue(
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str = REF_BRANCH,
) -> str:
    """Solves a single issue."""
    feature_branch: FeatureBranch = local_repo.new_feature_branch(
        ref_branch,
        feature_branch=_create_feature_branch_name(issue.no),
    )
    issue.add_comment(f"Assigned feature branch: `{feature_branch.name}`")

    start_time = time.time()
    try:
        result: DeepNextResult = deep_next_pipeline(
            problem_statement=issue.title + "\n" + issue.description,
            hints=issue.comments,
            root_dir=local_repo.repo_dir,
        )

        issue.add_comment(f"REASONING:\n\n{result.reasoning}")
        issue.add_comment(f"ACTION PLAN:\n\n{result.action_plan}")
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        issue.add_comment(msg)

    feature_branch.commit_all(
        commit_msg=f"DeepNext resolves #{issue.no}: {issue.title}"
    )
    feature_branch.push_to_remote()

    return feature_branch.name


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

    logger.debug(f"Looking for issues to be solved in '{vcs_config.repo_path}' project")
    if not (issues_todo := find_issues(vcs_connector, deep_next_label=TODO_LABEL)):
        logger.info(f"No issues to be solved for '{vcs_config.repo_path}' repo")
        return

    logger.success(
        f"Found {len(issues_todo)} issue(s) todo for '{vcs_config.repo_path}' repo: "
        f"{sorted(f'#{issue.no}' for issue in issues_todo)}"
    )

    failure = []
    success = []
    for issue in issues_todo:
        try:
            issue.add_label(IN_PROGRESS_LABEL)

            feature_branch = solve_issue(
                issue,
                local_repo,
                ref_branch=REF_BRANCH,
            )

            mr = vcs_connector.create_mr(
                merge_branch=feature_branch,
                into_branch=REF_BRANCH,
                title=f"[DeepNext] Resolve '{issue.title}'",
            )
        except Exception as e:
            failure.append(issue)

            err_msg = f"🔴 DeepNext app failed for #{issue.no}: {str(e)}"
            logger.error(err_msg)

            issue.add_label(FAILED_LABEL)
            issue.add_comment(
                comment=err_msg, file_content=str(e), file_name="error_message.txt"
            )
        else:
            success.append(issue)

            msg = f"🟢 Issue #{issue.no} solved: {mr.url}"
            logger.success(msg)

            issue.add_label(SOLVED_LABEL)
            issue.add_comment(msg)

        finally:
            issue.remove_label(IN_PROGRESS_LABEL)

    logger.success(
        f"Project '{vcs_config.repo_path}' summary: "
        f"total={len(issues_todo)}; solved={len(success)}; failed={len(failure)}"
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
