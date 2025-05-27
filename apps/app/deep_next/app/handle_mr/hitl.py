import json
import time
from enum import Enum, auto
from json import JSONDecodeError
from typing import Any

from deep_next.app.common import trim_comment_header
from deep_next.app.config import Label
from deep_next.app.git import GitRepository
from deep_next.app.handle_mr.messages import (
    _MSG_ACTION_PLAN_INVALID_FORMAT,
    MSG_TO_DEEP_NEXT_PREFIX,
    _msg_step_exec_time,
    is_msg_to_deep_next_ok,
    msg_action_plan_implemented,
    msg_action_plan_invalid_format,
    msg_deepnext_started,
    msg_present_action_plan,
    trim_msg_to_deep_next_prefix,
)
from deep_next.app.utils import convert_paths_to_str, convert_str_to_paths
from deep_next.connectors.version_control_provider import BaseMR
from deep_next.connectors.version_control_provider.base import BaseComment
from deep_next.core.graph_hitl import (
    deep_next_action_plan_graph,
    deep_next_implement_graph,
)
from deep_next.core.parser import extract_code_from_block, has_code_block
from deep_next.core.steps.action_plan.data_model import ActionPlan
from loguru import logger
from pydantic_core._pydantic_core import ValidationError


class ActionPlanParserError(Exception):
    """Action plan parser error."""


class _State(Enum):
    ACTION_PLAN_PROPOSITION_REQUEST = auto()
    AWAITING_HUMAN_FEEDBACK = auto()
    ACTION_PLAN_INVALID_FORMAT = auto()
    ACTION_PLAN_FIX_REQUEST = auto()
    ACTION_PLAN_IMPLEMENTATION_REQUEST = auto()


def _extract_action_plan_from_comment(
    comment: str,
) -> ActionPlan:
    """Extract action plan from the comment."""
    try:
        action_plan_reasoning = extract_code_from_block(
            comment, "action-plan-reasoning"
        )
        action_plan_steps = extract_code_from_block(comment, "action-plan-steps")

        action_plan_steps = json.loads(action_plan_steps)
        action_plan_steps = convert_str_to_paths(action_plan_steps)

        return ActionPlan.model_validate(
            {
                "reasoning": action_plan_reasoning,
                "ordered_steps": action_plan_steps,
            }
        )

    except (ValidationError, JSONDecodeError) as e:
        raise ActionPlanParserError(str(e))


def _get_last_action_plan(
    mr: BaseMR,
) -> tuple[BaseComment, list[BaseComment]] | tuple[None, None]:
    """Get the last action plan from the comments addressed to Deep Next."""
    succeeding_msgs_to_deep_next = []

    for comment in mr.comments[::-1]:

        if has_code_block(comment.body, "action-plan-reasoning") and has_code_block(
            comment.body, "action-plan-steps"
        ):
            return comment, succeeding_msgs_to_deep_next[::-1]
        elif comment.body.startswith(MSG_TO_DEEP_NEXT_PREFIX):
            succeeding_msgs_to_deep_next.append(comment)

    return None, None


def _determine_state(mr: BaseMR) -> tuple[_State, Any]:
    """
    Determine the state of the MR based on the comments.

    Return the state of the MR and the data needed to push it further towards
    completion.
    """
    last_action_plan_comment, succeeding_msgs_to_deep_next = _get_last_action_plan(mr)

    if last_action_plan_comment is None:
        return _State.ACTION_PLAN_PROPOSITION_REQUEST, None

    # For type hinting
    last_action_plan_comment: BaseComment
    succeeding_msgs_to_deep_next: list[BaseComment]

    if len(succeeding_msgs_to_deep_next) == 0:
        return _State.AWAITING_HUMAN_FEEDBACK, None

    comment_body = trim_comment_header(mr.comments[-1].body)
    if comment_body.startswith(_MSG_ACTION_PLAN_INVALID_FORMAT):
        return _State.ACTION_PLAN_INVALID_FORMAT, None

    if is_msg_to_deep_next_ok(succeeding_msgs_to_deep_next[-1]):
        return _State.ACTION_PLAN_IMPLEMENTATION_REQUEST, last_action_plan_comment

    return _State.ACTION_PLAN_FIX_REQUEST, (
        last_action_plan_comment,
        succeeding_msgs_to_deep_next,
    )


def _comment_action_plan(
    mr: BaseMR,
    action_plan: ActionPlan,
    execution_time: float | None = None,
    log: int | str | None = None,
) -> None:
    comment = msg_present_action_plan(action_plan)

    if execution_time:
        step_time_message = _msg_step_exec_time(
            execution_time, additional_info="Waiting for your response..."
        )
        comment += f"\n---\n{step_time_message}"

    mr.add_comment(comment, info_header=True, log=log)


def _propose_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
) -> tuple[ActionPlan, float]:
    """Propose an action plan."""
    start_time = time.time()
    issue = mr.related_issue
    action_plan = deep_next_action_plan_graph(
        root_path=local_repo.repo_dir,
        issue_title=issue.title,
        issue_description=issue.description,
        issue_comments=[comment.body for comment in issue.comments],
    )

    return action_plan, time.time() - start_time


def _fix_action_plan_prompt(
    old_action_plan: ActionPlan, edit_instructions: list[str]
) -> str:
    """Fix the action plan prompt."""
    edit_instructions = "\n\n".join(
        [f"- {instruction}" for instruction in edit_instructions]
    )

    return (
        f"The following action plan (describing how to complete the issue) was created:"
        f"\n```old-action-plan"
        f"\n{json.dumps(convert_paths_to_str(old_action_plan.model_dump()))}"
        f"\n```"
        f"\nUnfortunately, it turned out to be faulty. The task should be completed "
        f"following on a new action plan, fixed based collected feedback to the action "
        f"plan:"
        f"\n```edit-instructions"
        f"\n{edit_instructions}"
        f"\n```"
        f"\n"
        f"\nComplete the task by modifying the action plan to fulfill the task. Be as "
        f"precise as possible. Modify ONLY what has been mentioned in the feedback. "
        f"Precisely retain and copy each element of the old action plan if there were "
        f"no objections to it."
    )


def _fix_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    old_action_plan: ActionPlan,
    edit_instructions: list[str],
) -> tuple[ActionPlan, float]:
    """Fix the action plan."""
    issue = mr.related_issue

    if old_action_plan and edit_instructions:
        issue_comment = _fix_action_plan_prompt(old_action_plan, edit_instructions)
    else:
        issue_comment = ""

    start_time = time.time()
    action_plan = deep_next_action_plan_graph(
        root_path=local_repo.repo_dir,
        issue_title=issue.title,
        issue_description=issue.description,
        issue_comments=[issue_comment],
    )
    execution_time = time.time() - start_time
    return action_plan, execution_time


def _implement_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    action_plan_comment: str,
) -> float:
    """Implement an action plan."""
    action_plan = _extract_action_plan_from_comment(action_plan_comment)

    issue = mr.related_issue

    start_time = time.time()
    _ = deep_next_implement_graph(
        root_path=local_repo.repo_dir,
        issue_title=issue.title,
        issue_description=issue.description,
        issue_comments=[comment.body for comment in issue.comments],
        action_plan=action_plan,
    )
    exec_time = time.time() - start_time

    feature_branch = local_repo.get_feature_branch(mr.source_branch_name)
    feature_branch.commit_all(commit_msg=f"DeepNext resolves #{mr.no}: {mr.title}")
    feature_branch.push_to_remote()

    return exec_time


def handle_mr_human_in_the_loop(
    mr: BaseMR,
    local_repo: GitRepository,
) -> bool:
    """Handle MRs/PRs for the given issue."""
    state, data = _determine_state(mr)

    issue_no = mr.related_issue.no

    if state == _State.AWAITING_HUMAN_FEEDBACK:
        logger.info(f"🟡 Waiting for human feedback on issue #{issue_no}...")
        return True

    if state == _State.ACTION_PLAN_INVALID_FORMAT:
        logger.info(f"🟡 Waiting for last action plan fix or removal #{issue_no}...")
        return True

    mr.add_label(Label.IN_PROGRESS)

    try:
        if state == _State.ACTION_PLAN_PROPOSITION_REQUEST:
            mr.add_comment(msg_deepnext_started(), info_header=True)

            action_plan, execution_time = _propose_action_plan(mr, local_repo)
            _comment_action_plan(
                mr, action_plan, execution_time=execution_time, log="SUCCESS"
            )
            return True

        if state == _State.ACTION_PLAN_FIX_REQUEST:
            old_action_plan_comment: BaseComment = data[0]
            comments: list[BaseComment] = data[1]

            try:
                old_action_plan = _extract_action_plan_from_comment(
                    old_action_plan_comment.body
                )
            except ActionPlanParserError as e:
                mr.add_comment(
                    msg_action_plan_invalid_format(str(e)),
                    info_header=True,
                    log="WARNING",
                )
                return False

            action_plan, execution_time = _fix_action_plan(
                mr,
                local_repo,
                old_action_plan,
                [trim_msg_to_deep_next_prefix(c) for c in comments],
            )
            _comment_action_plan(
                mr, action_plan, execution_time=execution_time, log="SUCCESS"
            )
            return True

        if state == _State.ACTION_PLAN_IMPLEMENTATION_REQUEST:
            try:
                execution_time = _implement_action_plan(mr, local_repo, data)
                mr.add_comment(
                    msg_action_plan_implemented(execution_time),
                    info_header=True,
                    log="SUCCESS",
                )
                mr.add_label(Label.SOLVED)
                return True
            except ActionPlanParserError as e:
                mr.add_comment(
                    msg_action_plan_invalid_format(str(e)),
                    info_header=True,
                    log="WARNING",
                )
                return False

    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for MR #{mr.no}: {str(e)}"
        logger.error(err_msg)

        mr.add_label(Label.FAILED)
        mr.add_comment(comment=err_msg, info_header=True)

        return False
    finally:
        mr.remove_label(Label.IN_PROGRESS)
