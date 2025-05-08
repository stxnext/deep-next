from deep_next.common.llm import LLMConfigType, llm_from_config
from langchain_core.language_models import BaseChatModel


def _create_llm(seed: int | None = None) -> BaseChatModel:
    return llm_from_config(LLMConfigType.CODE_REVIEW, seed=seed)
