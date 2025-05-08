import json
import time
from enum import Enum, auto
from json import JSONDecodeError
from typing import Any

from pydantic_core._pydantic_core import ValidationError

from deep_next.app.common import trimm_comment_header
from deep_next.app.config import DeepNextLabel
from deep_next.app.git import GitRepository
from deep_next.app.utils import convert_paths_to_str
from deep_next.connectors.version_control_provider import BaseMR, BaseConnector
from deep_next.connectors.version_control_provider.base import BaseComment
from deep_next.core.graph_hitl import deep_next_action_plan_graph, deep_next_implement_graph
from loguru import logger

from deep_next.core.parser import has_code_block, extract_code_from_block
from deep_next.core.steps.action_plan.action_plan import create_action_plan
from deep_next.core.steps.action_plan.data_model import ActionPlan


class ActionPlanParserError(Exception):
    """Action plan parser error."""


class _State(Enum):
    ACTION_PLAN_PROPOSITION_REQUEST = auto()
    AWAITING_HUMAN_FEEDBACK = auto()
    ACTION_PLAN_INVALID_FORMAT = auto()
    ACTION_PLAN_FIX_REQUEST = auto()
    ACTION_PLAN_IMPLEMENTATION_REQUEST = auto()


MSG_TO_DEEPNEXT_PREFIX = "@deepnext"
MSG_TO_DEEPNEXT_CONTENT_OK = "OK"

MSG_ACTION_PLAN_INVALID_FORMAT = (
    "⚠️ The provided action plan has an invalid format."
    "\n"
    "\nPlease **fix it manually** or **remove** the proposed action plan AND then **remove THIS message**."
)

MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\nTo ACCEPT the action plan, respond with:"
    "\n```"
    f"\n{MSG_TO_DEEPNEXT_PREFIX}"
    f"\n{MSG_TO_DEEPNEXT_CONTENT_OK}"
    "\n```"
    "\n"
    "\nTo REQUEST CHANGES to the action plan, talk to DeepNext following the message format:"  # noqa: E501
    "\n```"
    f"\n{MSG_TO_DEEPNEXT_PREFIX}"
    "\n<message to DeepNext>"
    "\n```"
)


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

    if trimm_comment_header(mr.comments[-1].body).startswith(MSG_ACTION_PLAN_INVALID_FORMAT):
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
) -> None:
    pretty_action_plan = json.dumps(
        convert_paths_to_str(action_plan.model_dump()), indent=4
    )

    mr.add_comment(
        "## Action Plan"
        "\n```action-plan"
        f"\n{pretty_action_plan}"
        "\n```"
        f"\n{MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS}",
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
            issue_title=issue.title,
            issue_description=issue.description,
            issue_comments=[comment.body for comment in issue.comments],
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
    old_code_context: str,
    old_project_knowledge: str,
    edit_instructions: list[str],
) -> float:
    """Fix the action plan."""

    issue = mr.issue(vcs_connector)

    # create_action_plan(
    #     root_path=local_repo.repo_dir,
    #     issue_statement=issue.issue_statement,
    #     existing_code_context=old_code_context,
    #     project_knowledge=old_project_knowledge,
    # )


    if old_action_plan and edit_instructions:
        hints = (
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
    else:
        hints = ""

    start_time = time.time()
    try:
        action_plan = deep_next_action_plan_graph(
            root_path=local_repo.repo_dir,
            issue_title=issue.title,
            issue_description=issue.description,
            issue_comments=[hints],
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
    try:
        action_plan = ActionPlan.model_validate(json.loads(action_plan))
    except (ValidationError, JSONDecodeError) as e:
        raise ActionPlanParserError(str(e))

    issue = mr.issue(vcs_connector)

    start_time = time.time()
    try:
        _ = deep_next_implement_graph(
            root_path=local_repo.repo_dir,
            issue_title=issue.title,
            issue_description=issue.description,
            issue_comments=[comment.body for comment in issue.comments],
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
        logger.info(f"🟡 Waiting for human feedback on issue #{issue_no}...")
        return True

    if state == _State.ACTION_PLAN_INVALID_FORMAT:
        logger.info(f"🟡 Waiting for action plan fix or removal #{issue_no}...")
        return True

    mr.add_label(DeepNextLabel.IN_PROGRESS)

    success: bool
    try:
        if state == _State.ACTION_PLAN_PROPOSITION_REQUEST:
            execution_time = _propose_action_plan(mr, local_repo, vcs_connector)
            logger.success(
                f"🟢 Step for solving issue #{issue_no} finished."
                f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
            )

        elif state == _State.ACTION_PLAN_FIX_REQUEST:
            old_action_plan, comments = data
            execution_time = _fix_action_plan(
                mr,
                local_repo,
                vcs_connector,
                old_action_plan,
                "",
                "",
                comments
            )
            logger.success(
                f"🟢 Step for solving issue #{issue_no} finished."
                f"\nDeepNext core total execution time: {execution_time:.0f} seconds"
            )

        elif state == _State.ACTION_PLAN_IMPLEMENTATION_REQUEST:
            try:
                execution_time = _implement_action_plan(mr, local_repo, vcs_connector, data)
            except ActionPlanParserError as e:
                message = (
                    f"{MSG_ACTION_PLAN_INVALID_FORMAT}"
                    f"\n"
                    f"\n---"
                    f"\n```"
                    f"\n{str(e)}"
                    f"\n```"
                )
                logger.warning(message)
                mr.add_comment(message, info_header=True)
                return False

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
