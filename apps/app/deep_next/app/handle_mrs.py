import time

from deep_next.app.common import extract_issue_number_from_mr
from deep_next.app.config import DeepNextState
from deep_next.app.git import GitRepository
from deep_next.connectors.version_control_provider import BaseMR, BaseConnector
from loguru import logger

from deep_next.core.graph import deep_next_graph


def _solve_issue(
    mr: BaseMR,
    local_repo: GitRepository,
    connector: BaseConnector,
) -> float:
    """Solves a single issue."""
    mr.add_comment(f"DeepNext is onto it! Hold on...", info_header=True)

    issue = mr.issue(connector)
    if issue is None:
        raise ValueError(
            f"Cannot extract issue number from the MR description."
        )

    start_time = time.time()
    try:
        deep_next_graph(
            root=local_repo.repo_dir,
            problem_statement=issue.title + "\n" + issue.description,
            hints="",
        )
    finally:
        exec_time = time.time() - start_time

    feature_branch = local_repo.get_feature_branch(mr.source_branch_name)
    feature_branch.commit_all(
        commit_msg=f"DeepNext resolves #{mr.no}: {mr.title}"
    )
    feature_branch.push_to_remote()

    return exec_time


def handle_mr_e2e(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
):
    """
    Handle MRs/PRs for the given issue.
    """
    success: bool
    try:
        mr.add_label(DeepNextState.IN_PROGRESS)
        execution_time = _solve_issue(mr, local_repo, vcs_connector)
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for #{mr.no}: {str(e)}"
        logger.error(f"{err_msg}\n\n{e}")

        mr.add_label(DeepNextState.FAILED)
        mr.add_comment(
            comment=err_msg, info_header=True, # file_content=str(e), file_name="error_message.txt"
        )

        success = False
    else:
        msg = (
            f"🟢 Issue #{mr.no} solved."
           f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
        )
        logger.success(msg)

        mr.add_label(DeepNextState.SOLVED)
        mr.add_comment(msg, info_header=True)

        success = True
    finally:
        mr.remove_label(DeepNextState.IN_PROGRESS)

    return success