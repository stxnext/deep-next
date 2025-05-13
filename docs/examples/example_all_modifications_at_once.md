---
layout: default
title: All Modifications At Once
---

# All Modifications At Once

When implementing multiple changes across different files, current approach processes one file at a time. However, this can lead to suboptimal implementations when changes in different files are interconnected. This example demonstrates how to implement all modifications at once, allowing the language model to have a holistic view of the changes needed across the entire codebase.

## Implementation

This feature enhances the implementation process by developing patches for all files in a single LLM call, enabling better coordination and consistency across file changes.

### Step 1: Add Models and Imports

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class FilePatchModel(BaseModel):
    """Model for a single file patch."""

    file_path: str = Field(description="Absolute path to the file to modify")
    modifications: List[str] = Field(
        description="List of modifications to apply to this file"
    )


class MultiFilePatchesResult(BaseModel):
    """Model for developing patches across multiple files in a single run."""

    reasoning: str = Field(
        description="Reasoning behind the implementation approach across all files"
    )
    file_patches: List[FilePatchModel] = Field(
        description="List of files with their modifications"
    )
```

### Step 2: Create the All Patches Agent

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
def _create_all_patches_agent():
    """Creates LLM agent for developing all patches at once."""

    all_patches_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            textwrap.dedent("""
            You are a Senior Python Developer hired to implement changes across multiple files in a Python codebase.
            You will be given a list of steps to implement, each with a target file and description.
            Your task is to develop all the necessary patches for all files at once, considering the relationships and dependencies between files.

            DEVELOPMENT GUIDELINES
            ------------------------
            - Type Hints: Use type hints to enhance code clarity and maintainability
            - Docstrings: Include concise, informative single-line docstrings for all functions and methods
            - Line Length: Preferably fit in 88 chars in line
            - Pythonic Code: Embrace the Zen of Python by writing simple, readable, and direct code
            - Ensure consistency across all files, using similar patterns and conventions
            - Consider how changes in one file affect other files
            ------------------------

            BEST PRACTICES
            ------------------------
            - Implement Object-Oriented Programming (OOP) principles effectively
            - Write functions that are small, have clear purposes, and have meaningful names
            - Avoid hardcoded values; utilize configuration files or env variables
            - Ensure the code is easily testable and extendable
            - When implementing changes across multiple files, maintain a consistent approach
            - Remember that changes in one file may require corresponding changes in other files
            ------------------------
            """)
        ),
        (
            "human",
            textwrap.dedent("""
            TASK
            ------------------------
            Implement the following steps across multiple files:

            Issue Statement:
            {issue_statement}

            Steps to Implement:
            {steps_description}

            For each file, here is the current content:
            {files_content}
            ------------------------

            Your task is to develop patches for ALL files at once. Consider how changes in one file affect others.
            Think about:
            1. Dependencies between files
            2. Shared interfaces or classes
            3. Consistent naming and behavior across the codebase
            4. Overall system architecture

            OUTPUT FORMAT EXAMPLE
            ------------------------
            {example_output}
            ------------------------

            For each file, provide one or more modifications following the format shown in the example.
            Each modification should use the <file>, <original>, and <patched> tags.
            Include detailed reasoning about your implementation approach.
            """)
        ),
    ])

    parser = PydanticOutputParser(pydantic_object=MultiFilePatchesResult)

    return all_patches_prompt | _create_llm() | parser
```

### Step 3: Implement the Develop All Patches Function with output example

**Location**: `libs/core/deep_next/core/steps/implement/develop_patch.py`

```python
def develop_all_patches(steps: List[Step], issue_statement: str) -> str:
    """Develop patches for all steps in a single run.

    Args:
        steps: List of steps to implement
        issue_statement: The issue statement

    Returns:
        The combined raw patches text for all files
    """
    logger.info(f"Developing patches for {len(steps)} steps at once")

    for step in steps:
        if not step.target_file.exists():
            logger.warning(f"Creating new file: '{step.target_file}'")
            with open(step.target_file, "w") as f:
                f.write("# Comment added at creation time to indicate empty file.\n")

    steps_description = "\n".join([
        f"Step {i+1}: {step.title}\n"
        f"File: {step.target_file}\n"
        f"Description: {step.description}\n"
        for i, step in enumerate(steps)
    ])

    files_content = ""
    for step in steps:
        files_content += f"\nFile: {step.target_file}\n```python\n{read_txt(step.target_file)}\n```\n"


    result = _create_all_patches_agent().invoke(
        {
            "issue_statement": issue_statement,
            "steps_description": steps_description,
            "files_content": files_content,
            "example_output": example_output_multi_file_patches_result.model_dump_json()
        }
    )

    logger.info(f"Generated patches for {len(result.file_patches)} files")

    raw_modifications = "<modifications>\n"

    for file_patch in result.file_patches:
        for modification in file_patch.modifications:
            raw_modifications += modification.strip() + "\n\n"

    raw_modifications += "</modifications>"

    return raw_modifications

example_output_multi_file_patches_result = MultiFilePatchesResult(
    reasoning=textwrap.dedent("""
        The implementation addresses the requirements in multiple files:
        1. In file1.py, function_b is modified to have proper punctuation and another_function is updated to return a string.
        2. In file2.py, the MyClass initialization is enhanced to set a default value.
        These changes ensure consistent behavior across the codebase and improve the functionality.
        """),
    file_patches=[
        FilePatchModel(
            file_path="/path/to/file1.py",
            modifications=[
                textwrap.dedent("""
                # modification 1
                <file>/path/to/file1.py</file>
                <original>
                def function_a():
                    print("hello")

                def function_b():
                    print("World")
                </original>
                <patched>
                def function_a():
                    print("Hello")

                def function_b():
                    print("World!")
                </patched>
                """)
            ]
        ),
        FilePatchModel(
            file_path="/path/to/file2.py",
            modifications=[
                textwrap.dedent("""
                # modification 1
                <file>/path/to/file2.py</file>
                <original>
                class MyClass:
                    def __init__(self):
                        pass
                </original>
                <patched>
                class MyClass:
                    def __init__(self):
                        self.value = 42
                </patched>
                """)
            ]
        )
    ],
)
```

### Step 4: Add import

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
from deep_next.core.steps.implement.develop_patch import develop_all_patches
```

### Step 5: Update the Graph Implementation

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`


```python
class _Node(BaseNode):
    # ... existing methods ...

    @staticmethod
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        retry=tenacity.retry_if_exception_type((ApplyPatchError, ParsePatchesError)),
        reraise=True,
    )
    def develop_all_at_once(
        state: _State,
    ) -> _State:
        """Develop all patches for all steps at once."""
        raw_patches = develop_all_patches(
            steps=state.steps, issue_statement=state.issue_statement
        )

        patches: list[CodePatch] = parse_patches(raw_patches)
        patches = [patch for patch in patches if patch.before != patch.after]

        for patch in patches:
            apply_patch(patch)

        # Empty the steps_remaining list since we've processed all steps at once
        state.steps_remaining = []

        return state
```

### Step 6: Update _build method of ImplementGraph

**Location**: `libs/core/deep_next/core/steps/implement/graph.py`

```python
class ImplementGraph(BaseGraph):

    # ...

    def _build(self) -> None:
        self.add_quick_node(_Node.develop_all_at_once)
        self.add_quick_node(_Node.generate_git_diff)

        self.add_quick_edge(START, _Node.develop_all_at_once)
        self.add_quick_edge(_Node.develop_all_at_once, _Node.generate_git_diff)
        self.add_quick_edge(_Node.generate_git_diff, END)

    # ...

```

## Benefits

1. **Holistic Implementation**: The LLM considers all files at once, enabling better understanding of the relationships between files.

2. **Improved Consistency**: Changes across different files maintain consistent naming, patterns, and behavior.

3. **Better Dependency Management**: When one file depends on another, the changes are coordinated properly.

4. **Reduced Context Loss**: The LLM doesn't lose context when switching between files in separate calls.

5. **More Efficient**: Requires fewer LLM calls, potentially reducing time and cost.

6. **Deeper Reasoning**: The LLM can provide reasoning about the approach across the entire implementation, not just per file.

## Usage Example

### Implementing a Feature Across Multiple Files

```python
from pathlib import Path
from deep_next.core.steps.action_plan.data_model import ActionPlan, Step
from deep_next.core.steps.implement.graph import _Node, _State

steps = [
    Step(
        target_file=Path("./libs/core/tests/_resources/example_project/src/config.py").resolve(),
        title="Implement configuration settings",
        description="Add configuration for logging with loguru"
    ),
    Step(
        target_file=Path("./libs/core/tests/_resources/example_project/src/my_logger.py").resolve(),
        title="Create logger module",
        description="Create a logger using loguru with file and console output"
    ),
    Step(
        target_file=Path("./libs/core/tests/_resources/example_project/src/hello_world.py").resolve(),
        title="Use the logger",
        description="Use the logger in the main module to log application events"
    )
]

state = _State(
    root_path=Path("./deep-next"),
    issue_statement="Implement logging",
    steps=steps
)

_Node.develop_all_at_once(state=state)
```

In this example, the implementation step will process all three files at once, allowing the LLM to create a consistent logging implementation across the configuration, logger module, and main module files.

[Back to Examples](../examples.html)
