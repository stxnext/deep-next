from deep_next.app.config import Label
from deep_next.app.git import GitRepository
from deep_next.app.handle_mr.common import run_deepnext_pipeline
from deep_next.app.handle_mr.messages import msg_deepnext_started, msg_issue_solved
from deep_next.connectors.version_control_provider import BaseMR
from loguru import logger


def propose_solution_autonomously(mr: BaseMR, local_repo: GitRepository) -> None:
    """Main entry point to process an MR end-to-end via DeepNext."""
    mr.add_comment(msg_deepnext_started(), info_header=True)

    try:
        exec_time = run_deepnext_pipeline(mr, local_repo)
    except Exception as e:
        message = f"🔴 DeepNext failed on MR #{mr.no}: {str(e)}"
        logger.error(f"{message}\n\n{e}")

        mr.add_label(Label.FAILED)
        mr.add_comment(comment=message, info_header=True)
    else:
        mr.add_comment(
            comment=msg_issue_solved(exec_time=exec_time),
            info_header=True,
            log="SUCCESS",
        )
        mr.add_label(Label.SOLVED)
