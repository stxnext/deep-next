import time

from deep_next.app.git import GitRepository
from deep_next.connectors.version_control_provider import BaseMR
from deep_next.core.graph import deep_next_graph
from loguru import logger


def run_deepnext_pipeline(
    mr: BaseMR, repo: GitRepository, comments: list | None = None
) -> float:
    """Run DeepNext logic to solve the issue end-to-end. Returns execution time."""
    comments = comments if not None else []

    issue = mr.related_issue
    feature_branch = repo.get_feature_branch(mr.source_branch_name)

    logger.info(f"🔄 Starting DeepNext on issue #{issue.no}: {issue.title}")
    start_time = time.time()

    with feature_branch.create_changes(
        commit_msg=f"DeepNext resolved #{mr.no}: {mr.title}"
    ):
        deep_next_graph(
            root=repo.repo_dir,
            issue_title=issue.title,
            issue_description=issue.description,
            issue_comments=comments,
        )

    return time.time() - start_time
