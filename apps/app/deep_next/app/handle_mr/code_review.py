from deep_next.app.config import Label
from deep_next.app.git import GitRepository
from deep_next.app.handle_mr.common import run_deepnext_pipeline
from deep_next.connectors.version_control_provider import BaseMR
from deep_next.connectors.version_control_provider.base import CodeReviewCommentThread
from loguru import logger

CODE_REVIEW_REPLY_MESSAGE = ":white_check_mark: DeepNext is applying Your suggestion(s)"


def _format_thread_as_markdown(thread: CodeReviewCommentThread) -> str:
    comments = "\n".join(f"- {c.strip()}" for c in thread.comments if c.strip())

    return (
        f"### 📄 File: `{thread.file_path}`\n\n"
        f"💬 **Code review suggestions:**\n"
        f"{comments}\n\n"
        f"🧩 **Code snippet:**\n"
        f"```python\n{thread.code_lines.strip()}\n```"
    )


def apply_code_review(
    mr: BaseMR,
    local_repo: GitRepository,
) -> None:
    try:
        new_code_review_suggestions = [
            t
            for t in mr.extract_comment_threads()
            if CODE_REVIEW_REPLY_MESSAGE.lower() not in t.comments[-1].lower()
        ]
        if not new_code_review_suggestions:
            logger.info(f"No new code review suggestions found for MR #{mr.no}")
            return

        mr.add_comment("Found code review suggestions... applying", info_header=True)

        exec_time = run_deepnext_pipeline(
            mr=mr,
            repo=local_repo,
            comments=[
                _format_thread_as_markdown(thread)
                for thread in new_code_review_suggestions
            ],
        )

        for thread in new_code_review_suggestions:
            mr.reply_to_comment_thread(thread, body=CODE_REVIEW_REPLY_MESSAGE)

    except Exception as e:
        message = f"🔴 DeepNext app failed for MR #{mr.no}: {str(e)}"
        logger.error(f"{message}\n\n{e}")

        mr.add_comment(comment=message, info_header=True)
        mr.add_label(Label.FAILED)
    else:
        mr.add_comment(
            comment=(
                "Code review completed. "
                f"All suggestions applied within {exec_time:.0f} seconds.",
            ),
            info_header=True,
            log="SUCCESS",
        )
