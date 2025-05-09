import json
import time
from enum import Enum, auto
from json import JSONDecodeError
from typing import Any

from pydantic_core._pydantic_core import ValidationError

from deep_next.app.common import trimm_comment_header
from deep_next.app.config import DeepNextLabel
from deep_next.app.git import GitRepository
from deep_next.app.handle_mr.messages import msg_deepnext_started, \
    msg_action_plan_implemented, _msg_step_exec_time, msg_action_plan_invalid_format, \
    _MSG_ACTION_PLAN_INVALID_FORMAT, msg_present_action_plan, MSG_TO_DEEPNEXT_PREFIX, \
    MSG_TO_DEEPNEXT_CONTENT_OK
from deep_next.app.utils import convert_str_to_paths
from deep_next.connectors.version_control_provider import BaseMR, BaseConnector
from deep_next.connectors.version_control_provider.base import BaseComment
from deep_next.core.graph_hitl import deep_next_action_plan_graph, deep_next_implement_graph
from loguru import logger

from deep_next.core.parser import has_code_block, extract_code_from_block
from deep_next.core.steps.action_plan.data_model import ActionPlan


class ActionPlanParserError(Exception):
    """Action plan parser error."""


class _State(Enum):
    ACTION_PLAN_PROPOSITION_REQUEST = auto()
    AWAITING_HUMAN_FEEDBACK = auto()
    ACTION_PLAN_INVALID_FORMAT = auto()
    ACTION_PLAN_FIX_REQUEST = auto()
    ACTION_PLAN_IMPLEMENTATION_REQUEST = auto()


def _get_last_action_plan(mr: BaseMR) -> tuple[str, list[BaseComment]] | tuple[None, None]:
    """Get the last action plan from the comments addressed to Deep Next."""
    comments_after_action_plan = []

    for comment in mr.comments[::-1]:

        if has_code_block(comment.body, "action-plan"):
            action_plan = extract_code_from_block(comment.body, "action-plan")
            return action_plan, comments_after_action_plan[::-1]
        elif comment.body.startswith(MSG_TO_DEEPNEXT_PREFIX):
            comments_after_action_plan.append(comment)

    return None, None


def _determine_state(mr: BaseMR) -> tuple[_State, Any]:
    """
    Determine the state of the MR based on the comments.

    Return the state of the MR and the data needed to push it further towards
    completion.
    """

    last_action_plan, succeeding_comments = _get_last_action_plan(mr)

    if last_action_plan is None:
        return _State.ACTION_PLAN_PROPOSITION_REQUEST, None

    if len(succeeding_comments) == 0:
        return _State.AWAITING_HUMAN_FEEDBACK, None

    comment_body = trimm_comment_header(mr.comments[-1].body)
    if comment_body.startswith(_MSG_ACTION_PLAN_INVALID_FORMAT):
        return _State.ACTION_PLAN_INVALID_FORMAT, None

    succeeding_comments = [
        comment.body[len(MSG_TO_DEEPNEXT_PREFIX):].strip()
        for comment in succeeding_comments
    ]

    if succeeding_comments[-1].lower() == MSG_TO_DEEPNEXT_CONTENT_OK.lower():
        return _State.ACTION_PLAN_IMPLEMENTATION_REQUEST, last_action_plan

    return _State.ACTION_PLAN_FIX_REQUEST, (last_action_plan, succeeding_comments)


def _comment_action_plan(
    mr: BaseMR,
    action_plan: Any,
    execution_time: float | None = None,
    log: int | str | None = None,
) -> None:
    comment = msg_present_action_plan(action_plan)

    if execution_time:
        step_time_message = _msg_step_exec_time(execution_time, additional_info="Waiting for your response...")
        comment += (
            f"\n---"
            f"\n{step_time_message}"
        )

    mr.add_comment(comment, info_header=True, log=log)


def _propose_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
) -> tuple[ActionPlan, float]:
    """Propose an action plan."""
    start_time = time.time()
    issue = mr.issue(vcs_connector)
    action_plan = deep_next_action_plan_graph(
        root_path=local_repo.repo_dir,
        issue_title=issue.title,
        issue_description=issue.description,
        issue_comments=[comment.body for comment in issue.comments],
    )
    execution_time = time.time() - start_time
    return action_plan, execution_time


def _fix_action_plan_prompt(old_action_plan: str, edit_instructions: list[str]) -> str:
    """Fix the action plan prompt."""
    edit_instructions = "\n\n".join([f"- {instruction}" for instruction in edit_instructions])

    return (
        f"The following action plan (describing how to complete the issue) was created:"
        f"\n```old-action-plan"
        f"\n{old_action_plan}"
        f"\n```"
        f"\nUnfortunately, it turned out to be faulty. The task should be completed following on a new action plan, fixed based collected feedback to the action plan:"
        f"\n```edit-instructions"
        f"\n{edit_instructions}"
        f"\n```"
        f"\n"
        f"\nComplete the task by modifying the action plan to fulfill the task. Be as precise as possible. Modify ONLY what has been mentioned in the feedback. Precisely retain and copy each element of the old action plan if there were no objections to it."
    )

def _fix_action_plan(
    mr: BaseMR,
    local_repo: GitRepository,
    vcs_connector: BaseConnector,
    old_action_plan: str,
    edit_instructions: list[str],
) -> tuple[ActionPlan, float]:
    """Fix the action plan."""

    issue = mr.issue(vcs_connector)

    if old_action_plan and edit_instructions:
        issue_comment = _fix_action_plan_prompt()
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
    vcs_connector: BaseConnector,
    action_plan: str,
) -> float:
    """Implement an action plan."""
    try:
        action_plan = json.loads(action_plan)
        action_plan = convert_str_to_paths(action_plan)
        action_plan = ActionPlan.model_validate(action_plan)
    except (ValidationError, JSONDecodeError) as e:
        raise ActionPlanParserError(str(e))

    issue = mr.issue(vcs_connector)

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
    vcs_connector: BaseConnector,
) -> bool:
    """
    Handle MRs/PRs for the given issue.
    """
    state, data = _determine_state(mr)

    issue_no = mr.issue(vcs_connector).no

    if state == _State.AWAITING_HUMAN_FEEDBACK:
        logger.info(f"🟡 Waiting for human feedback on issue #{issue_no}...")
        return True

    if state == _State.ACTION_PLAN_INVALID_FORMAT:
        logger.info(f"🟡 Waiting for last action plan fix or removal #{issue_no}...")
        return True

    mr.add_label(DeepNextLabel.IN_PROGRESS)

    try:
        if state == _State.ACTION_PLAN_PROPOSITION_REQUEST:
            mr.add_comment(msg_deepnext_started(), info_header=True)

            action_plan, execution_time = _propose_action_plan(mr, local_repo, vcs_connector)
            _comment_action_plan(mr, action_plan, execution_time=execution_time, log='SUCCESS')
            return True

        if state == _State.ACTION_PLAN_FIX_REQUEST:
            old_action_plan, comments = data
            action_plan, execution_time = _fix_action_plan(
                mr,
                local_repo,
                vcs_connector,
                old_action_plan,
                comments
            )
            _comment_action_plan(mr, action_plan, execution_time=execution_time, log='SUCCESS')
            return True

        if state == _State.ACTION_PLAN_IMPLEMENTATION_REQUEST:
            try:
                execution_time = _implement_action_plan(mr, local_repo, vcs_connector, data)
                mr.add_comment(msg_action_plan_implemented(execution_time), info_header=True, log='SUCCESS')
                mr.add_label(DeepNextLabel.SOLVED)
                return True
            except ActionPlanParserError as e:
                mr.add_comment(msg_action_plan_invalid_format(str(e)), info_header=True, log='WARNING')
                return False

    except Exception as e:
        err_msg = f"🔴 DeepNext app failed for MR #{mr.no}: {str(e)}"
        logger.error(err_msg)

        mr.add_label(DeepNextLabel.FAILED)
        mr.add_comment(comment=err_msg, info_header=True)

        return False
    finally:
        mr.remove_label(DeepNextLabel.IN_PROGRESS)
