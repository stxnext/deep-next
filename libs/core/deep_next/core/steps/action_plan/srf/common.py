from deep_next.common.llm import LLMConfigType, llm_from_config
from langchain_core.language_models import BaseChatModel


def _create_llm_analyze(
    tools: list | None = None, seed: int | None = None
) -> BaseChatModel:
    llm = llm_from_config(LLMConfigType.SRF_ANALYZE, seed=seed)

    return llm.bind_tools(tools) if tools else llm


def _create_llm_tools(
    tools: list | None = None, seed: int | None = None
) -> BaseChatModel:
    llm = llm_from_config(LLMConfigType.SRF_TOOLS, seed=seed)

    return llm.bind_tools(tools) if tools else llm
