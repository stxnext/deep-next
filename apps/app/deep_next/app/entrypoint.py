import time
from datetime import datetime
from pathlib import Path

from deep_next.app.add_new_project import GitLabProjectConfig
from deep_next.app.config import (
    CONFIGS_DIR,
    FAILED_LABEL,
    FEATURE_BRANCH_NAME_TMPL,
    IN_PROGRESS_LABEL,
    REPOSITORIES_DIR,
    SOLVED_LABEL,
)
from deep_next.app.git import FeatureBranch, GitRepository, setup_local_git_repo
from deep_next.connectors.aws import AWSSecretsManager
from deep_next.connectors.gitlab_connector import GitLabConnector, GitLabIssue
from deep_next.core.entrypoint import main as deep_next_pipeline
from loguru import logger


def create_feature_branch_name(issue_no: int) -> str:
    """Creates a feature branch name for a given issue."""
    return FEATURE_BRANCH_NAME_TMPL.format(
        issue_no=issue_no,
        note=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
    )


def find_issues(
    gitlab_connector: GitLabConnector, deep_next_label: str
) -> list[GitLabIssue]:
    """Fetches all issues to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [FAILED_LABEL, SOLVED_LABEL, IN_PROGRESS_LABEL]

    resp = []
    for issue in gitlab_connector.list_issues(label=deep_next_label):
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


def solve_issue(
    gitlab_issue: GitLabIssue,
    local_repo: GitRepository,
    ref_branch: str = "develop",
) -> str:
    """Solves a single issue."""
    feature_branch: FeatureBranch = local_repo.new_feature_branch(
        ref_branch,
        feature_branch=create_feature_branch_name(gitlab_issue.no),
    )
    gitlab_issue.add_comment(f"Assigned feature branch: `{feature_branch.name}`")

    start_time = time.time()
    try:
        _ = deep_next_pipeline(
            problem_statement=gitlab_issue.title + "\n" + gitlab_issue.description,
            hints=gitlab_issue.comments,
            root_dir=local_repo.repo_dir,
        )
    finally:
        exec_time = time.time() - start_time

        msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
        logger.info(msg)
        gitlab_issue.add_comment(msg)

    feature_branch.commit_all(commit_msg=f"DeepNext resolves #{gitlab_issue.no}")
    feature_branch.push_to_remote()

    return feature_branch.name


def solve_project_issues(config: GitLabProjectConfig) -> None:
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

    logger.debug(f"Looking for issues to be solved in '{config.project_name}' project")
    if not (todo := find_issues(gitlab_project, deep_next_label=config.git.label)):
        logger.info(f"No issues to be solved for '{config.project_name}' repo")
        return

    logger.success(
        f"Found {len(todo)} issue(s) todo for '{config.project_name}' repo: "
        f"{sorted(f'#{issue.no}' for issue in todo)}"
    )

    failure = []
    success = []
    for gitlab_issue in todo:
        try:
            gitlab_issue.add_label(IN_PROGRESS_LABEL)

            feature_branch = solve_issue(
                gitlab_issue,
                local_repo,
                ref_branch=config.git.ref_branch,
            )

            mr = gitlab_project.create_mr(
                merge_branch=feature_branch,
                into_branch=config.git.ref_branch,
                title=f"Resolve '{gitlab_issue.title}'",
            )
        except Exception as e:
            failure.append(gitlab_issue)

            err_msg = f"🔴 DeepNext app failed for #{gitlab_issue.no}"
            logger.error(err_msg)
            gitlab_issue.add_comment(
                comment=err_msg, file_content=str(e), file_name="error_message.txt"
            )

            gitlab_issue.add_label(FAILED_LABEL)
        else:
            success.append(gitlab_issue)

            msg = f"🟢 Issue #{gitlab_issue.no} solved: {mr.web_url}"
            logger.success(msg)
            gitlab_issue.add_comment(msg)

            gitlab_issue.add_label(SOLVED_LABEL)
        finally:
            gitlab_issue.remove_label(IN_PROGRESS_LABEL)

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
            solve_project_issues(config)

    logger.success("DeepNext app run completed.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
