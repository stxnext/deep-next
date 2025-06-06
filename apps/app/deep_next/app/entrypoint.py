from deep_next.app.common import create_feature_branch_name
from deep_next.app.config import REF_BRANCH, REPOSITORIES_DIR, Label
from deep_next.app.git import FeatureBranch, GitRepository, setup_local_git_repo
from deep_next.app.handle_mr.autonomous import propose_solution_autonomously
from deep_next.app.handle_mr.code_review import apply_code_review
from deep_next.app.handle_mr.hitl import (
    handle_mr_human_in_the_loop as work_on_action_plan,
)
from deep_next.app.utils import get_connector
from deep_next.app.vcs_config import VCSConfig, load_vcs_config_from_env
from deep_next.common.cmd import run_command
from deep_next.connectors.version_control_provider import BaseIssue, BaseMR
from loguru import logger


def _create_empty_commit(feature_branch: FeatureBranch) -> None:
    """Creates an empty commit to allow MR creation when the branch has no changes."""
    run_command(
        [
            "git",
            "commit",
            "--allow-empty",
            "-m",
            "chore: empty commit to initialize MR",
        ],
        cwd=feature_branch.repo_dir,
    )
    feature_branch.push_to_remote()


def create_mr(
    vcs_config: VCSConfig,
    issue: BaseIssue,
    local_repo: GitRepository,
    ref_branch: str,
    labels: list[Label],
) -> BaseMR:
    """Creates a merge request for the given issue."""
    try:
        feature_branch: FeatureBranch = local_repo.new_feature_branch(
            ref_branch,
            feature_branch=create_feature_branch_name(issue.no),
        )
        logger.info(f"Feature branch created: '{feature_branch.name}'")

        _create_empty_commit(feature_branch)

        vcs_connector = get_connector(vcs_config)  # TODO: Move to a common place
        mr = vcs_connector.create_mr(
            merge_branch=feature_branch.name,
            into_branch=ref_branch,
            title=f"[DeepNext] Resolve issue #{issue.no}: {issue.title}",  # TODO
            description="This is description for the MR created by DeepNext.",
            issue=issue,
        )

        issue.remove_label(Label.TODO)

        for label in labels:
            mr.add_label(label)

    except Exception as e:
        message = f"🔴 Failed to create MR/PR:\n\n{e}"
        logger.error(message)
        issue.add_comment(message, info_header=True)

        return

    message = (
        f"Assigned feature branch: `{feature_branch.name}`\n"
        f"🟢 Issue #{issue.no} solution: {mr.url}"
    )
    logger.success(message)
    issue.add_comment(message, info_header=True)

    return mr


def prepare_mr(issues: list[BaseIssue], vcs_config: VCSConfig) -> None:
    """Solves issues dedicated for DeepNext for given project."""
    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )

    for idx, issue in enumerate(issues, start=1):
        logger.info(
            f"({idx}/{len(issues)}) Preparing mr for issue #{issue.no}: '{issue.title}'"
        )

        run_type_label = (
            Label.HUMAN_IN_THE_LOOP
            if issue.has_label(Label.HUMAN_IN_THE_LOOP)
            else Label.AUTONOMOUS
        )
        logger.info(
            f"Issue #{issue.no} run type: {run_type_label.name}, creating MR..."
        )

        mr = create_mr(
            vcs_config,
            issue,
            local_repo,
            ref_branch=REF_BRANCH,
            labels=[run_type_label, Label.IN_PROGRESS],
        )

        if not run_type_label == Label.AUTONOMOUS:
            return

        propose_solution_autonomously(
            mr=mr,
            local_repo=local_repo,
        )


def main() -> None:
    """Solves issues dedicated for DeepNext for given project."""
    vcs_config: VCSConfig = load_vcs_config_from_env()
    vcs_connector = get_connector(vcs_config)

    logger.info(f"Starting DeepNext app for '{vcs_config.repo_path}' repo")

    # TODO: Making it class based, we can have common variables behind self.
    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,
    )

    if issues_todo := vcs_connector.list_issues(label=Label.TODO):
        logger.info(
            f"Found {len(issues_todo)} issues with '{Label.TODO}' label "
            f"in '{vcs_config.repo_path}'"
        )
        prepare_mr(issues_todo, vcs_config)

    if mrs_in_progress := vcs_connector.list_mrs(label=Label.IN_PROGRESS):
        logger.info(
            f"Found {len(mrs_in_progress)} MRs with '{Label.IN_PROGRESS}' label "
            f"in '{vcs_config.repo_path}'"
        )
        for mr in mrs_in_progress:
            work_on_action_plan(mr=mr, local_repo=local_repo)

    if mrs_code_review := vcs_connector.list_mrs(
        label=Label.SOLVED
    ):  # TODO: Ready for code review
        for mr in mrs_code_review:
            apply_code_review(
                mr=mr,
                local_repo=local_repo,
            )

    logger.success(f"DeepNext app run completed for '{vcs_config.repo_path}' repo")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
