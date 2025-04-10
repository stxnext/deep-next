from pathlib import Path

from deep_next.common.llm import LLMConfigType, llm_from_config
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field


def _create_llm(seed: int | None = None) -> BaseChatModel:
    return llm_from_config(LLMConfigType.SRS_ANALYZE, seed=seed)


class FileCodeContext(BaseModel):
    path: Path = Field(description="Path to the file")
    reasoning: str = Field(description="Reasoning for the code context")
    localization_code_snippet: str = Field(
        description="Class, function, or line of code that needs to be edited"
        " or is directly related to the issue."
    )


class ExistingCodeContext(BaseModel):
    overview_description: str = Field(description="Overview of the code context")
    code_context: list[FileCodeContext] = Field(
        default_factory=list, description="Code context for localization"
    )

    def dump(self) -> str:
        return "\n".join(
            [
                f"{file_context.path}\n{file_context.localization_code_snippet}\n"
                for file_context in self.code_context
            ]
        )
