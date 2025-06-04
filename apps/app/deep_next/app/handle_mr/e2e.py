import time

from deep_next.app.config import Label
from deep_next.app.git import GitRepository
from deep_next.app.handle_mr.messages import msg_deepnext_started, msg_issue_solved
from deep_next.connectors.version_control_provider import BaseMR
from deep_next.core.graph import deep_next_graph
from loguru import logger


def _solve_issue_e2e(
    mr: BaseMR,
    local_repo: GitRepository,
) -> float:
    """Solves a single issue."""
    mr.add_comment(msg_deepnext_started(), info_header=True)

    issue = mr.related_issue
    if issue is None:
        raise ValueError("Cannot extract issue number from the MR description.")

    start_time = time.time()
    try:
        deep_next_graph(
            root=local_repo.repo_dir,
            issue_title=issue.title,
            issue_description=issue.description,
            issue_comments=[],
        )
    finally:
        exec_time = time.time() - start_time

    feature_branch = local_repo.get_feature_branch(mr.source_branch_name)
    feature_branch.commit_all(commit_msg=f"DeepNext resolved #{mr.no}: {mr.title}")
    feature_branch.push_to_remote()

    return exec_time


def handle_mr_e2e(
    mr: BaseMR,
    local_repo: GitRepository,
):
    """Handle MRs/PRs for the given issue."""
    try:
        mr.add_label(Label.IN_PROGRESS)
        exec_time = _solve_issue_e2e(mr, local_repo)
    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for MR #{mr.no}: {str(e)}"
        logger.error(f"{err_msg}\n\n{e}")

        mr.add_label(Label.FAILED)
        mr.add_comment(comment=err_msg, info_header=True)

        return False
    else:
        mr.add_comment(
            msg_issue_solved(exec_time=exec_time), info_header=True, log="SUCCESS"
        )
        mr.add_label(Label.SOLVED)

        return True
    finally:
        mr.remove_label(Label.IN_PROGRESS)
