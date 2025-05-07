import json
import time
from enum import Enum, auto
from typing import Any

from deep_next.app.common import trimm_comment_header
from deep_next.app.config import DeepNextLabel
from deep_next.app.git import GitRepository
from deep_next.app.utils import convert_paths_to_str
from deep_next.connectors.version_control_provider import BaseMR, BaseConnector
from deep_next.connectors.version_control_provider.base import BaseComment
from deep_next.core.graph_hitl import deep_next_action_plan_graph, deep_next_implement_graph
from loguru import logger

from deep_next.core.parser import has_code_block, extract_code_from_block
from deep_next.core.steps.action_plan.data_model import ActionPlan


class _State(Enum):
    PROPOSE_ACTION_PLAN = auto()
    AWAITING_HUMAN_FEEDBACK = auto()
    FIX_ACTION_PLAN = auto()
    IMPLEMENT_ACTION_PLAN = auto()


MESSAGE_TO_DEEPNEXT_PREFIX = "@deepnext"

ACTION_PLAN_PREFIX = "## Action Plan"
ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\nTo ACCEPT the action plan, respond with:"
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\nOK"
    "\n```"
    "\n"
    "\nTo REQUEST CHANGES to the action plan, talk to DeepNext using the following message format:"  # noqa: E501
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\n<message to deepnext>"
    "\n```"
)


def _get_last_action_plan(mr: BaseMR) -> tuple[str, list[BaseComment]] | tuple[None, None]:
    """Get the last action plan from the comments addressed to Deep Next."""
    comments_after_action_plan = []

    for comment in mr.comments[::-1]:

        comment_body = trimm_comment_header(comment.body)

        if has_code_block(comment_body, "action-plan"):
            action_plan = extract_code_from_block(comment_body, "action-plan")
            return action_plan, comments_after_action_plan[::-1]
        elif comment_body.startswith(MESSAGE_TO_DEEPNEXT_PREFIX):
            comments_after_action_plan.append(comment)

    return None, None


def _determine_state(mr: BaseMR) -> tuple[_State, Any]:
    """
    Determine the state of the MR based on the comments.
    """

    last_action_plan, succeeding_comments = _get_last_action_plan(mr)

    if last_action_plan is None:
        return _State.PROPOSE_ACTION_PLAN, None

    if len(succeeding_comments) == 0:
        return _State.AWAITING_HUMAN_FEEDBACK, None

    succeeding_comments = [
        comment.body[len(MESSAGE_TO_DEEPNEXT_PREFIX):].strip()
        for comment in succeeding_comments
    ]

    if succeeding_comments[-1].lower() == "ok":
        return _State.IMPLEMENT_ACTION_PLAN, last_action_plan

    return _State.FIX_ACTION_PLAN, (last_action_plan, succeeding_comments)

def _comment_action_plan(
    mr: BaseMR,
    action_plan: Any,
) -> None:
    pretty_action_plan = json.dumps(
        convert_paths_to_str(action_plan.model_dump()), indent=4
    )

    mr.add_comment(
        f"{ACTION_PLAN_PREFIX}"
        f"\n```action-plan"
        f"\n{pretty_action_plan}"
        f"\n```"
        f"\n{ACTION_PLAN_RESPONSE_INSTRUCTIONS}",
        info_header=True
    )

def _propose_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
) -> float:
    """Propose an action plan."""
    start_time = time.time()
    try:
        issue = mr.issue(vcs_connector)
        action_plan = deep_next_action_plan_graph(
            root_path=local_repo.repo_dir,
            problem_statement=issue.title + "\n" + issue.description,
        )
    finally:
        exec_time = time.time() - start_time

    _comment_action_plan(mr, action_plan)

    return exec_time


def _fix_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
    old_action_plan: str,
    edit_instructions: list[str],
) -> float:
    """Fix the action plan."""

    if old_action_plan and edit_instructions:
        hints = (
            f"Edit the action plan:"
            f"\n```"
            f"\n{old_action_plan}"
            f"\n```"
            f"\nwith instructions:"
            f"\n```"
            f"\n{edit_instructions}"
            f"\n```"
        )
    else:
        hints = ""

    start_time = time.time()
    try:
        issue = mr.issue(vcs_connector)
        action_plan = deep_next_action_plan_graph(
            root_path=local_repo.repo_dir,
            problem_statement=issue.title + "\n\n" + issue.description,
            hints=hints
        )
    finally:
        exec_time = time.time() - start_time

    _comment_action_plan(mr, action_plan)

    return exec_time


def _implement_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
    action_plan: str,
) -> float:
    """Implement an action plan."""
    action_plan = ActionPlan.model_validate(json.loads(action_plan))

    start_time = time.time()
    try:
        issue = mr.issue(vcs_connector)
        _ = deep_next_implement_graph(
            root_path=local_repo.repo_dir,
            problem_statement=issue.title + "\n\n" + issue.description,
            action_plan=action_plan,
        )
    finally:
        exec_time = time.time() - start_time

    feature_branch = local_repo.get_feature_branch(mr.source_branch_name)
    feature_branch.commit_all(commit_msg=f"DeepNext resolves #{mr.no}: {mr.title}")
    feature_branch.push_to_remote()

    return exec_time


def handle_mr_human_in_the_loop(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
) -> bool:
    """
    Handle MRs/PRs for the given issue.
    """
    state, data = _determine_state(mr)

    issue_no = mr.issue(vcs_connector).no

    if state == _State.AWAITING_HUMAN_FEEDBACK:
        logger.success(f"🟡 Waiting for human feedback on issue #{issue_no}...")
        return True

    mr.add_label(DeepNextLabel.IN_PROGRESS)

    success: bool
    try:
        if state == _State.PROPOSE_ACTION_PLAN:
            execution_time = _propose_action_plan(mr, local_repo, vcs_connector)
            logger.success(
                f"🟢 Step for issue #{issue_no} finished."
                f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
            )

        elif state == _State.FIX_ACTION_PLAN:
            old_action_plan, comments = data
            execution_time = _fix_action_plan(mr, local_repo, vcs_connector, old_action_plan, comments)
            logger.success(
                f"🟢 Step for issue #{issue_no} finished."
                f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
            )

        elif state == _State.IMPLEMENT_ACTION_PLAN:
            execution_time = _implement_action_plan(mr, local_repo, vcs_connector, data)
            logger.success(
                f"🟢 Issue #{issue_no} solved."
                f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
            )

        success = True

    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for MR #{mr.no}: {str(e)}"
        logger.error(err_msg)

        mr.add_label(DeepNextLabel.FAILED)
        mr.add_comment(comment=err_msg, info_header=True)

        success = False
    finally:
        mr.remove_label(DeepNextLabel.IN_PROGRESS)

    return success
