from deep_next.common.llm import LLMConfigType, llm_from_config
from langchain_core.language_models import BaseChatModel
from typing import List

def _create_llm(seed: int | None = None) -> BaseChatModel:
    return llm_from_config(LLMConfigType.ACTION_PLAN, seed=seed)


def format_action_plan_for_comment(action_plan: "ActionPlan") -> str:
    """Format ActionPlan as Markdown for PR/MR comment."""
    reasoning = getattr(action_plan, "reasoning", None)
    steps = getattr(action_plan, "steps", None)

    md = "# 🧠 DeepNext Action Plan\n"
    if reasoning:
        md += "\n## Reasoning\n"
        md += f"{reasoning}\n"
    if steps:
        md += "\n## Steps\n"
        for idx, step in enumerate(steps, 1):
            md += f"{idx}. {step}\n"
    return md
