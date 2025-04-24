---
layout: default
title: Additional Context File Detection
---

# Additional Context File Detection

When implementing changes to a file, the language model might need additional context from related files to fully understand the requirements and implement the solution correctly. This example demonstrates how to automatically detect and provide additional context files to the implementation phase.

## Implementation

This feature enhances the implementation process by automatically detecting when related files need to be examined for proper implementation. It adds a new node to the implementation graph that analyzes the task and determines if additional files should be included as context.

### Step 1: Add imports

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
from typing import List, Optional
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
```

### Step 2: Add the Context Files Detection Model

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
class ContextFilesResult(BaseModel):
    """Model for determining additional context files needed for implementation."""

    needs_additional_context: bool = Field(
        description="Whether additional context files are needed for implementation"
    )
    reasoning: str = Field(
        description="Detailed reasoning for why these files are needed for context"
    )
    additional_files: List[str] = Field(
        default_factory=list,
        description="List of additional file paths that should be included for context"
    )
```

### Step 3: Create a Context File Detection Agent

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
def _create_context_files_agent():
    """Creates LLM agent for detecting needed context files."""
    context_files_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert Python developer analyzing implementation tasks.
                Your job is to determine if additional context files are needed to properly
                implement a task in a target file.

                You need to carefully analyze:
                1. The task description
                2. The target file's content
                3. The list of available implementation steps

                You will decide if additional context files are needed to properly understand
                and implement the task. These could include:
                - Files that define interfaces the target file must implement
                - Files that contain related functionality
                - Files that define types or models used in the target file
                - Configuration or utility files needed to understand the implementation
                """,
            ),
            (
                "human",
                """Please analyze the following implementation task:

                Target File: {target_file}

                File Content:
                {file_content}

                Task Title: {task_title}
                Task Description: {task_description}
                Issue Statement: {issue_statement}

                All Implementation Steps:
                {all_steps}

                Your task is to determine if additional context files are needed to properly
                implement this task. Consider files that:
                1. Define interfaces, base classes, or types used by the target file
                2. Contain related functionality that the implementation must interact with
                3. Import or use the target file (to understand how it's used)
                4. Define configuration or environment that affects implementation

                EXAMPLE OUTPUT:
                {additional_context_example}

                If no additional context is needed, return:

                {no_additional_context_example}
                """,
            ),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ContextFilesResult)

    return context_files_prompt | _create_llm() | parser


additional_context_example = ContextFilesResult(
    needs_additional_context=True,
    reasoning="File1 defines the interface that must be implemented. File2 contains utility functions needed for the implementation.",
    additional_files=[
        "/absolute/path/to/file1.py",
        "/absolute/path/to/file2.py"     ]
)

no_additional_context_example = ContextFilesResult(
    needs_additional_context=False,
    reasoning="The target file is self-contained and the task can be implemented with the current context.",
    additional_files=[]
)
```

### Step 3: Add Functions to Identify and Load Context Files

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
def identify_context_files(
    step: Step,
    issue_statement: str,
    all_steps: List[Step]
) -> ContextFilesResult:
    """Identify additional context files needed for implementation.

    Args:
        step: The step to implement
        issue_statement: The issue statement
        all_steps: All steps in the implementation plan

    Returns:
        ContextFilesResult with identified context files
    """
    if not step.target_file.exists():
        logger.warning(f"Target file '{step.target_file}' doesn't exist, can't identify context files")
        return ContextFilesResult(
            needs_additional_context=False,
            additional_files=[],
            reasoning="Target file doesn't exist, can't analyze for context files"
        )

    # Format all steps for the prompt
    all_steps_formatted = "\n".join([
        f"- Step: {s.title}\n  File: {s.target_file}\n  Description: {s.description}"
        for s in all_steps
    ])

    result = _create_context_files_agent().invoke(
        {
            "target_file": step.target_file,
            "file_content": read_txt(step.target_file),
            "task_title": step.title,
            "task_description": step.description,
            "issue_statement": issue_statement,
            "all_steps": all_steps_formatted,
            "additional_context_example": additional_context_example.model_dump_json(),
            "no_additional_context_example": no_additional_context_example.model_dump_json(),
        }
    )

    logger.info(f"Context files analysis result: {result}")
    return result


def load_context_files(files: List[str]) -> dict[Path, str]:
    """Load the content of the identified context files.

    Args:
        files: List of file paths to load

    Returns:
        Dict mapping file paths to their content
    """
    context_files = {}

    for file_path in files:
        path = Path(file_path)
        if path.exists():
            logger.info(f"Loading context file: {path}")
            context_files[path] = read_txt(path)
        else:
            logger.warning(f"Context file not found: {path}")

    return context_files
```

### Step 4: Update the Single File Patches Function

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
def develop_single_file_patches(
    step: Step,
    issue_statement: str,
    context_files: Optional[dict[Path, str]] = None
) -> str:
    """Develop patches for a single file.

    Args:
        step: The step to implement
        issue_statement: The issue statement
        context_files: Optional dict of additional context files {path: content}

    Returns:
        The raw patches text
    """
    if not step.target_file.exists():
        logger.warning(f"Creating new file: '{step.target_file}'")

        with open(step.target_file, "w") as f:
            f.write("# Comment added at creation time to indicate empty file.\n")

    input_data = {
        "path": step.target_file,
        "code_context": read_txt(step.target_file),
        "high_level_description": step.title,
        "description": step.description,
        "issue_statement": issue_statement,
    }

    # Add additional context files if provided
    if context_files:
        additional_context = ""
        for context_file_path, content in context_files.items():
            additional_context += f"\nAdditional context file: {context_file_path}\n"
            additional_context += "```python\n"
            additional_context += content
            additional_context += "\n```\n"
            additional_context += "Note: This file is provided for context only. Do not modify it.\n"

        # Append the additional context to the issue statement
        input_data["issue_statement"] = (
            input_data["issue_statement"]
            + "\n\n--- ADDITIONAL CONTEXT FILES ---\n"
            + additional_context
        )

    raw_edits = _create_llm_agent().invoke(input_data)

    return raw_edits
```

### Step 5. Add imports

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
from deep_next.core.steps.implement.develop_patch import (
    ContextFilesResult,
    identify_context_files,
    load_context_files,
)
from pathlib import Path
```

### Step 6: Update the State Class in the Implementation Graph

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
class _State(BaseModel):
    root_path: Path = Field(description="Path to the root project directory.")
    issue_statement: str = Field(
        description="Detailed description of the issue to be implemented."
    )
    steps: list[Step] = Field(description="List of steps to implement the solution.")

    steps_remaining: list[Step] | None = Field(
        default=None, description="Steps yet to be processed."
    )
    selected_step: Step | None = Field(
        default=None, description="The step currently being processed."
    )

    context_files: dict[Path, str] | None = Field(
        default=None, description="Additional context files for implementation."
    )

    git_diff: str | None = Field(
        default=None,
        description="The resulting git diff after applying the implementation steps.",
    )
```

### Step 7: Update the _Node to add Context File Detection Node and modify code_development

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
class _Node(BaseNode):
    @staticmethod
    def select_next_step(state: _State) -> dict:
        step: Step = state.steps_remaining.pop(0)

        return {"selected_step": step}

    @staticmethod
    def identify_context_files(state: _State) -> dict:
        """Identify additional context files needed for implementation."""
        context_files_result = identify_context_files(
            step=state.selected_step,
            issue_statement=state.issue_statement,
            all_steps=state.steps,
        )

        context_files = None
        if context_files_result.needs_additional_context and context_files_result.additional_files:
            context_files = load_context_files(context_files_result.additional_files)
        return {
            "context_files": context_files,
        }

    @staticmethod
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        retry=tenacity.retry_if_exception_type((ApplyPatchError, ParsePatchesError)),
        reraise=True,
    )
    def code_development(
        state: _State,
    ) -> _State:
        raw_patches = develop_single_file_patches(
            step=state.selected_step,
            issue_statement=state.issue_statement,
            context_files=state.context_files,
        )

        patches: list[CodePatch] = parse_patches(raw_patches)
        patches = [patch for patch in patches if patch.before != patch.after]

        for patch in patches:
            apply_patch(patch)

        return state

    @staticmethod
    def generate_git_diff(state: _State) -> dict:
        return {"git_diff": generate_diff(state.root_path)}
```

### Step 8: Update the Graph Building Logic

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
def _build(self) -> None:
    self.add_quick_node(_Node.select_next_step)
    self.add_quick_node(_Node.identify_context_files)
    self.add_quick_node(_Node.code_development)
    self.add_quick_node(_Node.generate_git_diff)

    self.add_quick_edge(START, _Node.select_next_step)
    self.add_quick_edge(_Node.select_next_step, _Node.identify_context_files)
    self.add_quick_edge(_Node.identify_context_files, _Node.code_development)
    self.add_quick_edge(_Node.generate_git_diff, END)

    self.add_quick_conditional_edges(_Node.code_development, _select_next_or_end)
```

## Benefits

1. **Improved Context Awareness**: The LLM can make better implementation decisions when it has access to related files that provide necessary context.

2. **Reduced Hallucinations**: With more context about related components, the LLM is less likely to make incorrect assumptions about how the code should work.

3. **Better Interface Compliance**: When implementing files that must conform to interfaces or base classes, having those definitions available ensures the implementation is compatible.

4. **Enhanced Code Quality**: Understanding related files helps the LLM maintain consistent coding styles and approaches across the project.

5. **More Accurate Fixes**: For bug fixes that span multiple files, understanding the full context leads to more comprehensive solutions.

## Usage Example

To run example prepare placeholder `loger.py` file in `./libs/core/tests/_resources/example_project/src/logger.py`.
Add `# placeholder for logger.py` to the file.

```python
from deep_next.core.steps.implement.graph import _Node, _State
from deep_next.core.steps.action_plan.data_model import Step
from pathlib import Path


steps = [
    Step(
        target_file=Path("./libs/core/tests/_resources/example_project/src/logger.py").resolve(),
        title="Write logger",
        description=("Prepare a logger. User loguru library. Add option to log to "
                     "file and console. Log to console by default.")
    ),
    Step(
        target_file=Path("./libs/core/tests/_resources/example_project/src/hello_world.py").resolve(),
        title="Add logging",
        description="Add logging to each function in the hello_world.py file"
    )
]

state = _State(
    root_path=Path("./deep-next"),
    issue_statement="Add logging",
    steps=steps,
    selected_step=steps[1]
)

_Node.identify_context_files(state=state)
```

[Back to Examples](../examples.html)
