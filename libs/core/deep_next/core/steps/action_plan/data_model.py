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
    reasoning: str
    ordered_steps: list[Step]

    def to_markdown(self) -> str:
        """Format reasoning and steps as markdown for user-friendly display."""
        steps_md = "\n".join(
            [
                f"**{idx+1}. {step.title}**\n"
                f"{step.description}\n"
                f"_Target file_: `{step.target_file}`\n"
                for idx, step in enumerate(self.ordered_steps)
            ]
        )
        return (
            f"### Reasoning\n"
            f"{self.reasoning}\n\n"
            f"### Steps\n"
            f"{steps_md}"
        )
