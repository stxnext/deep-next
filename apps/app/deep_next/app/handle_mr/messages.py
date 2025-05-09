import json

from deep_next.app.utils import convert_paths_to_str
from deep_next.core.steps.action_plan.data_model import ActionPlan


def msg_deepnext_started() -> str:
    return "🚀 DeepNext is onto it! **Hold on**..."

def _msg_deep_next_exec_time(exec_time: float) -> str:
    return f"> ⏱️ DeepNext core execution time: {exec_time:.0f} seconds."

def _msg_step_exec_time(exec_time: float, additional_info: str | None = None) -> str:
    base_message = "🟢 Step finished."
    if additional_info:
        base_message += f" {additional_info}"

    return (
        f"{base_message}"
        f"\n{_msg_deep_next_exec_time(exec_time)}"
    )

def msg_issue_solved(exec_time: float | None = None) -> str:
    base_message = "🎉 **Issue solved!** See you next time!"

    if exec_time:
        return (
            f"{base_message}"
            f"\n{_msg_deep_next_exec_time(exec_time)}"
        )

    return base_message


MSG_TO_DEEPNEXT_PREFIX = "@deepnext"
MSG_TO_DEEPNEXT_CONTENT_OK = "OK"

MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\nTo **ACCEPT** the action plan, respond with:"
    "\n```"
    f"\n{MSG_TO_DEEPNEXT_PREFIX}"
    f"\n{MSG_TO_DEEPNEXT_CONTENT_OK}"
    "\n```"
    "\n"
    "\nTo **REQUEST CHANGES** to the action plan, talk to DeepNext following the message format:"  # noqa: E501
    "\n```"
    f"\n{MSG_TO_DEEPNEXT_PREFIX}"
    "\n<message to DeepNext>"
    "\n```"
)

def msg_present_action_plan(action_plan: ActionPlan) -> str:
    pretty_action_plan = json.dumps(
        convert_paths_to_str(action_plan.model_dump()), indent=4
    )

    return (
        "## Action Plan"
        "\nWhat do you think about the action plan below?"
        "\n```action-plan"
        f"\n{pretty_action_plan}"
        "\n```"
        f"\n{MSG_ACTION_PLAN_RESPONSE_INSTRUCTIONS}"
    )

_MSG_ACTION_PLAN_INVALID_FORMAT = (
    "⚠️ The provided action plan has an invalid format."
    "\n"
    "\nPlease **fix it manually** or **remove** the proposed action plan AND then **remove THIS message**."
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