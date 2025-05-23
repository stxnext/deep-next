from copy import deepcopy
from pathlib import Path
from typing import Literal

import tenacity
from deep_next.core.base_graph import BaseGraph
from deep_next.core.config import IMPLEMENTATION_MODE, ImplementationModes
from deep_next.core.steps.action_plan.data_model import ActionPlan, Step
from deep_next.core.steps.implement.apply_patch.apply_patch import apply_patch
from deep_next.core.steps.implement.apply_patch.common import ApplyPatchError
from deep_next.core.steps.implement.develop_patch import (
    ParsePatchesError,
    develop_all_patches,
    develop_single_file_patches,
    parse_patches,
)
from deep_next.core.steps.implement.git_diff import generate_diff
from deep_next.core.steps.implement.utils import CodePatch
from langgraph.graph import END, START
from loguru import logger
from pydantic import BaseModel, Field, model_validator


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

    git_diff: str | None = Field(
        default=None,
        description="The resulting git diff after applying the implementation steps.",
    )

    @model_validator(mode="after")
    def initialize_steps_remaining(self) -> "_State":
        if self.steps_remaining is None:
            self.steps_remaining = deepcopy(self.steps)
        return self


class _Node:
    @staticmethod
    def select_next_step(state: _State) -> dict:
        step: Step = state.steps_remaining.pop(0)

        logger.info(
            f"Implementing solution for: '{step.title}'\n"
            f"Description: {step.description}"
        )

        return {"selected_step": step, "steps_remaining": state.steps_remaining}

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
            git_diff=(
                generate_diff(state.root_path)
                or "<Empty Git Diff, no modifications found>"
            ),
        )

        patches: list[CodePatch] = parse_patches(raw_patches)
        patches = [patch for patch in patches if patch.before != patch.after]

        for patch in patches:
            apply_patch(patch)

        return state

    @staticmethod
    def generate_git_diff(state: _State) -> dict:
        return {"git_diff": generate_diff(state.root_path)}

    @staticmethod
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
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


def _select_next_or_end(
    state: _State,
) -> Literal[_Node.select_next_step.__name__, _Node.generate_git_diff.__name__]:
    if state.steps_remaining:
        logger.debug(f"Steps remaining: {len(state.steps_remaining)}")
        return _Node.select_next_step.__name__

    logger.success("Implementation completed, generating diff...")

    return _Node.generate_git_diff.__name__


def _select_implementation_mode() -> Literal[
    _Node.select_next_step.__name__, _Node.develop_all_at_once.__name__
]:
    if IMPLEMENTATION_MODE == ImplementationModes.SINGLE_FILE:
        return _Node.select_next_step.__name__
    else:
        return _Node.develop_all_at_once.__name__


class ImplementGraph(BaseGraph):
    """Implementation of "Implement" step in LangGraph."""

    def __init__(self):
        super().__init__(_State)

    def _build(self) -> None:
        # Add nodes for both implementation modes
        self.add_quick_node(_Node.select_next_step)
        self.add_quick_node(_Node.code_development)
        self.add_quick_node(_Node.develop_all_at_once)
        self.add_quick_node(_Node.generate_git_diff)

        # Add conditional edge from START based on implementation mode
        self.add_quick_conditional_edges(START, _select_implementation_mode)

        # # SINGLE_FILE path
        self.add_quick_edge(_Node.select_next_step, _Node.code_development)
        self.add_quick_conditional_edges(_Node.code_development, _select_next_or_end)

        # ALL_AT_ONCE path
        self.add_quick_edge(_Node.develop_all_at_once, _Node.generate_git_diff)

        # Common end point
        self.add_quick_edge(_Node.generate_git_diff, END)

    def create_init_state(
        self, root_path: Path, issue_statement: str, action_plan: ActionPlan
    ) -> _State:
        return _State(
            root_path=root_path,
            issue_statement=issue_statement,
            steps=action_plan.ordered_steps,
        )

    def __call__(
        self, root_path: Path, issue_statement: str, action_plan: ActionPlan
    ) -> str:
        initial_state = self.create_init_state(root_path, issue_statement, action_plan)
        final_state: _State = self.compiled.invoke(initial_state)

        return _State.model_validate(final_state).git_diff


implement_graph = ImplementGraph()

if __name__ == "__main__":
    print(f"Saved to: {implement_graph.visualize(subgraph_depth=3)}")
