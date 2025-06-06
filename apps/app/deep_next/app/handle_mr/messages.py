import json
import textwrap

from deep_next.app.utils import convert_paths_to_str
from deep_next.connectors.version_control_provider.base import BaseComment
from deep_next.core.steps.action_plan.data_model import ActionPlan


def msg_deepnext_started() -> str:
    return "🚀 DeepNext is onto it! **Hold on**..."


def _msg_deep_next_exec_time(exec_time: float) -> str:
    return f"> ⏱️ DeepNext core execution time: {exec_time:.0f} seconds."


def _msg_step_exec_time(exec_time: float, additional_info: str | None = None) -> str:
    base_message = "🟢 Step finished."
    if additional_info:
        base_message += f" {additional_info}"

    return f"{base_message}" f"\n{_msg_deep_next_exec_time(exec_time)}"


def msg_issue_solved(exec_time: float | None = None) -> str:
    base_message = "🎉 **Issue solved!** See you next time!"

    if exec_time:
        return f"{base_message}" f"\n{_msg_deep_next_exec_time(exec_time)}"

    return base_message


MSG_TO_DEEP_NEXT_PREFIX = "@deepnext"


def trim_msg_to_deep_next_prefix(msg: str | BaseComment) -> str:
    """Trims the DeepNext prefix from the message."""
    msg = msg.body if isinstance(msg, BaseComment) else msg
    if msg.startswith(MSG_TO_DEEP_NEXT_PREFIX):
        return msg[len(MSG_TO_DEEP_NEXT_PREFIX) + 1 :].strip()
    return msg.strip()


MSG_TO_DEEP_NEXT_CONTENT_OK = "OK"


def is_msg_to_deep_next_ok(msg: str | BaseComment) -> bool:
    """Checks if the message is a response to DeepNext and if it is OK."""
    msg = msg.body if isinstance(msg, BaseComment) else msg
    trimmed_msg = trim_msg_to_deep_next_prefix(msg)
    return trimmed_msg.lower() == MSG_TO_DEEP_NEXT_CONTENT_OK.lower()


MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\n👌 To **ACCEPT** the action plan, respond with:"
    "\n```"
    f"\n{MSG_TO_DEEP_NEXT_PREFIX}"
    f"\n{MSG_TO_DEEP_NEXT_CONTENT_OK}"
    "\n```"
    "\n"
    "\n✏️ To **REQUEST CHANGES** to the action plan, talk to DeepNext following the message format:"  # noqa: E501
    "\n```"
    f"\n{MSG_TO_DEEP_NEXT_PREFIX}"
    "\n<message to DeepNext>"
    "\n```"
)


def msg_present_action_plan(action_plan: ActionPlan) -> str:
    ordered_steps_json = [step.model_dump() for step in action_plan.ordered_steps]
    ordered_steps_json = convert_paths_to_str(ordered_steps_json)

    reasoning = "\n".join(
        textwrap.fill(line, width=88, replace_whitespace=False)
        for line in action_plan.reasoning.splitlines()
    )

    return (
        "## Reasoning (for context only)"
        "\n```action-plan-reasoning"
        f"\n{reasoning}"
        "\n```"
        "\n## Action Plan"
        "\nWhat do you think about the action plan below?"
        "\n```action-plan-steps"
        f"\n{json.dumps(ordered_steps_json, indent=4)}"
        "\n```"
        f"\n{MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS}"
    )


_MSG_ACTION_PLAN_INVALID_FORMAT = (
    "⚠️ The provided action plan has an invalid format."
    "\n"
    "\nPlease **fix it manually** or **remove** the proposed action plan AND then "
    "**remove THIS message**."
)


def msg_action_plan_invalid_format(err_msg: str) -> str:
    return (
        f"{_MSG_ACTION_PLAN_INVALID_FORMAT}"
        f"\n"
        f"\n---"
        f"\n```"
        f"\n{err_msg}"
        f"\n```"
    )


def msg_action_plan_implemented(execution_time: float) -> str:
    return (
        "💾 Action plan successfully implemented."
        "\n"
        "\n---"
        f"\n{_msg_step_exec_time(execution_time)}"
        "\n"
        "\n---"
        f"\n{msg_issue_solved()}"
    )
