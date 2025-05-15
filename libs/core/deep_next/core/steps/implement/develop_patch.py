from __future__ import annotations

import difflib
import textwrap
from pathlib import Path
from typing import List

from deep_next.core.io import read_txt
from deep_next.core.parser import has_tag_block, parse_tag_block
from deep_next.core.steps.action_plan.data_model import Step
from deep_next.core.steps.implement import acr
from deep_next.core.steps.implement.common import _create_llm
from deep_next.core.steps.implement.utils import CodePatch
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger


class Prompt:
    task_description = textwrap.dedent(
        """
        You are a Senior Python Developer hired to contribute into an existing Python codebase.
        Your only responsibility is to write source code.

        Ensure that each piece of the code you modify integrates seamlessly with the whole system.
        Improve modules one by one, with respect to modifications details given by your colleague solution designer.

        DEVELOPMENT GUIDELINES
        ------------------------
        - Type Hints: Use type hints to enhance code clarity and maintainability.
        {task_description_1}
        - Line Length: Preferably fit in 88 chars in line.
        - Pythonic Code: Embrace the Zen of Python by writing simple, readable, and direct code.
        ------------------------

        BEST PRACTICES
        ------------------------
        - Implement Object-Oriented Programming (OOP) principles effectively, particularly those from the SOLID principles.
        - Write functions that are small, have clear purposes, and bear meaningful names.
        - Avoid hardcoded values; instead, utilize configuration files or env variables.
        - Ensure the code is easily testable and extendable, preparing for possible future requirements.
        ------------------------
        """  # noqa: E501
    )

    expected_input_data_description = textwrap.dedent(
        """
        EXPECTED INPUT DATA
        ------------------------
        1. File To Change
        The specific file assigned to you that requires modifications.
        {expected_input_data_description_1}
        2. High-lvl description
        High-level description of necessary changes in a given file.

        3. Detailed Description
        Additional requirements needed in the module to meet the expectations.

        4. Issue statement
        {expected_input_data_description_2}
        ------------------------
        """  # noqa: E501
    )

    input_data = textwrap.dedent(
        """
        INPUT DATA
        ------------------------
        ```
        {code_context}
        ```

        <high_level_description>
        {high_level_description}
        </high_level_description>

        <description>
        {description}
        </description>

        <issue_statement>
        {issue_statement}
        </issue_statement>
        {git_diff}
        ------------------------
        """
    )

    expected_output_format = textwrap.dedent(
        """
        EXPECTED OUTPUT
        ------------------------
        Write a patch for the issue, based on the retrieved context.

        Within `<file>...</file>`, replace `...` with actual absolute file path.

        Within `<original>...</original>`, replace `...` with the only and exactly the \
        same fragment of code without losing any details, mind spaces gaps and \
        comments. It must be a substring of the original file - don't change any sign.

        The `<original>...</original>` code must be at least 5 lines. It will be used \
        to identify the exact location of the code to be replaced. The code will be \
        replaced using the exact match procedure with respect to the lines so DO NOT \
        change ANY sign.

        Within `<patched>...</patched>` code, pay attention to indentation, it's \
        Python code.

        {single_modification_output_format}

        If you want to add new code, DO NOT output only empty line in the 'original' \
        block. Use part of the existing code near which you want to add the new code. \
        Remember to put the same part of the existing code in the 'patched' field in \
        order to preserve the original code.

        You can import necessary libraries.

        Note: It's allowed to write multiple modifications for one file.
        ------------------------
        """  # noqa: E501
    )

    # TODO: remove `But don't produce multiple modifications for the same code snippet`
    #   when handling multiple modifications for the same code snippet is solved
    modifications_specific_guidelines = textwrap.dedent(
        """
        MODIFICATIONS SPECIFIC GUIDELINES
        ------------------------
        - Remember that `<original>...</original>` will be replaced with `<patched>...</patched>`.
        - Multiple small modifications are better than one big modification.
        - Don't produce multiple modifications for the same code snippet, preventing overlapping changes.
        - Focus on one function/method at the time.
        - Don't address the whole file in one modification. Split into multiple logical peaces.
        - Single modification should consist only of code relevant to itself.
        - Only produce modifications that introduce a change!
        - Do not make type hints and doc strings changes if they are not required by the task.
        - Pay attention to the git diff of the previous modifications made by other developers. They are related to the same task you are part of, and may be worth building upon.
        ------------------------
        """  # noqa: E501
    )

    modifications_example = textwrap.dedent(
        """
        MODIFICATIONS EXAMPLE
        ------------------------
        ## File to change

        File: /home/patryk/my_project/src/hello_world.py
        ```python
        def say_hello():
            \"\"\"Say hello!\"\"\"
            print("Hello World")


        def log(msg: str) -> None:
            print(f">>> {{msg}}")


        def foo() -> str:
            return "bar"


        def add_integers(a, b):
            return int(a + b)
        ```

        {logger_file_example}

        ----------
        ## Goal
        {multiple_modification_code_example}
        Introduce Python 3.11 syntax type hints and implement remove_integers function.

        ## Modifications
        <modifications>
        # modification 1
        <file>/home/patryk/my_project/src/hello_world.py</file>
        <original>
        def say_hello():
            \"\"\"Say hello!\"\"\"
            print("Hello World")

        def log(msg: str) -> None:
            print(f">>> {{msg}}")
        </original>
        <patched>
        def say_hello() -> None:
            \"\"\"Say hello!\"\"\"
            print("Hello World")

        def log(msg: str) -> None:
            print(f">>> {{msg}}")
        </patched>

        # modification 2
        <file>/home/patryk/my_project/src/hello_world.py</file>
        <original>
        def foo() -> str:
            return "bar"


        def add_integers(a, b):
            return int(a + b)
        </original>
        <patched>
        def foo() -> str:
            return "bar"


        def add_integers(a: int, b: int) -> int:
            \"\"\"Add two integers.\"\"\"
            return int(a + b)
        </patched>

        # modification 3
        <file>/home/patryk/my_project/src/hello_world.py</file>
        <original>
        def foo() -> str:
            return "bar"


        def add_integers(a: int, b: int) -> int:
            \"\"\"Add two integers.\"\"\"
            return int(a + b)
        </original>
        <patched>
        def foo() -> str:
            return "bar"


        def add_integers(a: int, b: int) -> int:
            \"\"\"Add two integers.\"\"\"
            return int(a + b)


        def remove_integers(a: int, b: int) -> int:
            \"\"\"Subtract two integers.\"\"\"
            return int(a - b)
        </patched>
        </modifications>
        ------------------------

        Notice that in # modification 2 type hints and docstrings were added to the \
        `add_integers` function and this is reflected in the # modification 3.
        If your task is to implement new function then attach context of the file \
        where this function should be implemented, i.e. `remove_integers` function.
        """
    )


def _create_llm_agent():
    """Creates LLM agent for project description task."""
    develop_changes_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", Prompt.task_description),
            ("human", Prompt.expected_input_data_description),
            ("human", Prompt.input_data),
            ("human", Prompt.expected_output_format),
            ("human", Prompt.modifications_specific_guidelines),
            ("human", Prompt.modifications_example),
        ]
    )

    parser = StrOutputParser()

    return develop_changes_prompt_template | _create_llm() | parser


class ParsePatchesError(Exception):
    """Raised for issues encountered during parse patches process."""


def develop_single_file_patches(step: Step, issue_statement: str, git_diff: str) -> str:
    if not step.target_file.exists():
        logger.warning(f"Creating new file: '{step.target_file}'")

        with open(step.target_file, "w") as f:
            f.write("# Comment added at creation time to indicate empty file.\n")

    task_description_1 = textwrap.dedent(
        """- Docstrings: Include concise, informative single-line docstrings for all new functions and methods (if task doesn't state differently)."""  # noqa: E501
    )

    single_modification_output_format = textwrap.dedent(
        """
    The requested modifications you are assigned with are part of a larger coding \
    task. For context, you are given the task issue statement. Some code changes \
    have already been made for the task by other developers. When developing the \
    your modifications, build upon the changes made so far (if plausible).
    """
    )

    expected_input_data_description_1 = textwrap.dedent(
        """
    This is part a larger task and you are responsible for only this file.
    """
    )

    expected_input_data_description_2 = textwrap.dedent(
        """
    Original issue that defines the full task, from which this file-specific step was derived.
    Gives broader context to better understand why the change is needed.

    5. Related Changes (Git Diff)
    A summary of changes from earlier steps in this task, shown as a Git diff.
    Helps identify reusable code or utilities already implemented in other files, so you can avoid duplication and improve consistency.
    """  # noqa: E501
    )

    raw_edits = _create_llm_agent().invoke(
        {
            "code_context": (
                f"File path: '{step.target_file}'\n{read_txt(step.target_file)}"
            ),
            "high_level_description": step.title,
            "description": step.description,
            "issue_statement": issue_statement,
            "single_modification_output_format": single_modification_output_format,
            "logger_file_example": "",
            "multiple_modification_code_example": "",
            "task_description_1": task_description_1,
            "git_diff": f" <git_diff>\n{git_diff}\n</git_diff>",
            "expected_input_data_description_1": expected_input_data_description_1,
            "expected_input_data_description_2": expected_input_data_description_2,
        }
    )

    return raw_edits


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

    steps_description = "\n".join(
        [
            f"Step {i+1}: {step.title}\n"
            f"File: {step.target_file}\n"
            f"Description: {step.description}\n"
            for i, step in enumerate(steps)
        ]
    )

    files_content = ""
    for step in steps:
        files_content += (
            f"\nFile: {step.target_file}\n"
            f"```python\n{read_txt(step.target_file)}\n```\n"
        )

    task_description_1 = textwrap.dedent(
        """- Docstrings: Include concise, informative single-line docstrings for all functions and methods."""  # noqa: E501
    )

    logger_file_example = textwrap.dedent(
        """
        File: /home/patryk/my_project/src/logger.py
        ```python
        # Placeholder for code content
        ```

        """
    )

    multiple_modification_code_example = textwrap.dedent(
        """
        Implement logger and add logging functionality to the `say_hello` function in `hello_world.py`.

        ## Modifications
        <modifications>
        # modification 1
        <file>/home/patryk/my_project/src/logger.py</file>
        <original>
        # Placeholder for code content
        </original>
        <patched>
        from loguru import logger
        logger.add("file.log", rotation="1 MB")

        def log(msg: str) -> None:
            logger.info(f">>> {{msg}}")
        </patched>
        # modification 2
        <file>/home/patryk/my_project/src/hello_world.py</file>
        <original>
        def say_hello():
            \"\"\"Say hello!\"\"\"
            print("Hello World")
        </original>
        <patched>
        def say_hello():
            \"\"\"Say hello!\"\"\"
            print("Hello World")
            log("Hello World printed")
        </patched>

        ----------
        ## Goal (Another example)
        """  # noqa: E501
    )

    expected_input_data_description_2 = textwrap.dedent(
        """Completes the context for better understanding given requirements."""
    )

    raw_modifications = _create_llm_agent().invoke(
        {
            "issue_statement": issue_statement,
            "description": steps_description,
            "code_context": files_content,
            "high_level_description": step.title,
            "single_modification_output_format": "",
            "logger_file_example": logger_file_example,
            "multiple_modification_code_example": multiple_modification_code_example,
            "task_description_1": task_description_1,
            "git_diff": "",
            "expected_input_data_description_1": "",
            "expected_input_data_description_2": expected_input_data_description_2,
        }
    )

    return raw_modifications


def _git_diff(before: str, after: str, path: str) -> str:
    """Generate unified git diff between two strings.

    Example:
        > _git_diff(
            before = 'def say_hello():\n    print("Hello World")',
            after = 'def say_hello() -> None:\n    print("Hello World")',
            path="hello_world.py"
        )
        '''
        --- hello_world.py
        +++ hello_world.py
        @@ -1,2 +1,2 @@
        -def say_hello():
        +def say_hello() -> None:
             print("Hello World")
        '''
    """
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=path,
            tofile=path,
            lineterm="",
        )
    )


def parse_patches(txt: str) -> list[CodePatch]:
    if not has_tag_block(txt, "modifications"):
        raise ParsePatchesError(
            f"Response does not contain any modifications code block: {txt}"
        )

    edits_text = parse_tag_block(txt, "modifications")

    try:
        edits: list[acr.Edit] = acr.parse_edits(edits_text)
    except Exception as e:
        raise ParsePatchesError(f"Exception happened when parsing edits: {e}") from e

    if not edits:
        raise ParsePatchesError(f"Engineer failed to provide modifications: {txt}")

    # TODO: Validate it's current file edit
    # TODO: Validate path exists

    return [
        CodePatch(
            file_path=Path(edit.filename),
            before=edit.before,
            after=edit.after,
            diff=_git_diff(edit.before, edit.after, edit.filename),
        )
        for edit in edits
    ]
