from pathlib import Path

from pydantic import BaseModel, Field


class FileCodeContext(BaseModel):
    path: Path
    code_snippet: str
    explanation: str = ""


class ExistingCodeContext(BaseModel):
    code_context: list[FileCodeContext] = Field(default_factory=list)

    def dump(self) -> str:
        return "\n".join(
            [
                f"Path: {file_context.path}\n"
                f"Explanation: {file_context.explanation}\n"
                f"Code:\n{file_context.code_snippet}\n"
                for file_context in self.code_context
            ]
        )


class Step(BaseModel):
    title: str = Field(description="High level step overview.")
    description: str = Field(description="Detailed step description.")
    target_file: Path = Field(description="Absolute path to the file to be modified.")


class ActionPlan(BaseModel):
    reasoning: str = Field(
        description="Explanation of the rationale behind the action plan, "
        "intended for both human and machine readability."
    )
    ordered_steps: list[Step] = Field(
        description="List of steps to be executed in order, each step "
        "providing a high-level overview and detailed description."
    )
