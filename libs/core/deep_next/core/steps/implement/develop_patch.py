from __future__ import annotations

import difflib
from pathlib import Path
from typing import List

from deep_next.common.llm import LLMConfigType, create_llm
from deep_next.common.llm_retry import invoke_retriable_llm_chain
from deep_next.core.io import read_txt
from deep_next.core.parser import has_tag_block, parse_tag_block
from deep_next.core.steps.action_plan.data_model import Step
from deep_next.core.steps.implement import acr
from deep_next.core.steps.implement.apply_patch.apply_patch import apply_patch
from deep_next.core.steps.implement.apply_patch.common import ApplyPatchError
from deep_next.core.steps.implement.prompt_all_at_once_implemetation import (
    PromptAllAtOnceImplementation,
)
from deep_next.core.steps.implement.prompt_single_file_implementation import (
    PromptSingleFileImplementation,
)
from deep_next.core.steps.implement.utils import CodePatch
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger


class ApplyPatchValidator(BaseOutputParser):

    root_path: Path

    def __init__(self, root_path: Path, **kwargs):
        super().__init__(root_path=root_path, **kwargs)
        self.root_path = root_path

    def parse(self, text: str) -> str:
        parse_and_apply_patches(text, self.root_path, dry_run=True)
        return text


def _create_llm_chain(
    root_path: Path,
    prompt: type[PromptSingleFileImplementation] | type[PromptAllAtOnceImplementation],
    seed: int | None = None,
):
    """Creates LLM agent for project description task."""
    develop_changes_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt.task_description),
            ("human", prompt.expected_input_data_description),
            ("human", prompt.input_data),
            ("human", prompt.expected_output_format),
            ("human", prompt.modifications_specific_guidelines),
            ("human", prompt.modifications_example),
        ]
    )

    return (
        develop_changes_prompt_template
        | create_llm(LLMConfigType.IMPLEMENT, seed)
        | StrOutputParser()
        | ApplyPatchValidator(root_path)
    )


class ParsePatchesError(Exception):
    """Raised for issues encountered during parse patches process."""


def _create_new_files(step: Step, root_path: Path) -> None:
    for target_file in step.target_files:
        if not (root_path / target_file).exists():
            logger.warning(f"Creating new file: '{root_path / target_file}'")

            with open(root_path / target_file, "w") as f:
                f.write("# Comment added at creation time to indicate empty file.\n")


def develop_single_file_patches(
    step: Step, issue_statement: str, git_diff: str, root_path: Path, n_retry: int = 3
) -> str:
    _create_new_files(step, root_path)

    code_context = "\n\n\n---\n\n\n".join(
        [
            f"{str(target_file)}:\n\n```{read_txt(root_path / target_file)}```"
            for target_file in step.target_files
        ]
    )

    data = {
        "code_context": code_context,
        "high_level_description": step.title,
        "description": step.description,
        "issue_statement": issue_statement,
        "git_diff": git_diff,
    }

    raw_patches = invoke_retriable_llm_chain(
        n_retry=n_retry,
        llm_chain_builder=lambda seed: _create_llm_chain(
            root_path, PromptSingleFileImplementation, seed
        ),
        prompt_arguments=data,
        exception_type=(ApplyPatchError, ParsePatchesError),
    )

    return raw_patches


def develop_all_patches(
    steps: List[Step], issue_statement: str, root_path: Path, n_retry: int = 3
) -> str:
    """Develop patches for all steps in a single run.

    Args:
        steps: List of steps to implement
        issue_statement: The issue statement
        root_path: The root path of the project
        n_retry: Number of retries for the LLM chain

    Returns:
        The combined raw patches text for all files
    """
    logger.info(f"Developing patches for {len(steps)} steps at once")

    for step in steps:
        _create_new_files(step, root_path)

    steps_description = "\n".join(
        [
            f"# Step {i}: {step.title}\n"
            f"# Files:\n{', '.join([str(file) for file in step.target_files])}\n"
            f"# Description:\n{step.description}\n"
            for i, step in enumerate(steps, start=1)
        ]
    )

    target_files = []
    for step in steps:
        target_files.extend(step.target_files)

    files_content = ""
    for target_file in target_files:
        markdown_style = "python" if target_file.suffix == ".py" else "txt"
        try:
            file_content = read_txt(root_path / target_file)
        except Exception as e:
            logger.warning(f"Failed to read file {target_file}: {e}")
            file_content = ""
        files_content += (
            f"\nFile: {target_file}\n" f"```{markdown_style}\n{file_content}\n```\n"
        )

    data = {
        "issue_statement": issue_statement,
        "description": steps_description,
        "code_context": files_content,
    }

    raw_patches = invoke_retriable_llm_chain(
        n_retry=n_retry,
        llm_chain_builder=lambda seed: _create_llm_chain(
            root_path, PromptAllAtOnceImplementation, seed
        ),
        prompt_arguments=data,
        exception_type=(ApplyPatchError, ParsePatchesError),
    )

    return raw_patches


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


def parse_and_apply_patches(
    raw_patches: str, root_path: Path, dry_run: bool = False
) -> None:
    """Parse and apply patches to the codebase."""
    patches: list[CodePatch] = parse_patches(raw_patches)
    patches = [patch for patch in patches if patch.before != patch.after]

    for patch in patches:
        apply_patch(patch, root_path, dry_run)
