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

        logger.info(f"Implementing solution for: '{step.title}'")

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
            step=state.selected_step, issue_statement=state.issue_statement
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


def _select_next_or_end(
    state: _State,
) -> Literal[_Node.select_next_step.__name__, _Node.generate_git_diff.__name__]:
    if state.steps_remaining:
        logger.debug(f"Steps remaining: {len(state.steps_remaining)}")
        return _Node.select_next_step.__name__

    logger.success("Implementation completed, generating diff...")

    return _Node.generate_git_diff.__name__


class ImplementGraph(BaseGraph):
    """Implementation of "Implement" step in LangGraph."""

    def __init__(self):
        super().__init__(_State)

    def _build(self) -> None:
        if IMPLEMENTATION_MODE == ImplementationModes.SINGLE_FILE:
            self.add_quick_node(_Node.select_next_step)
            self.add_quick_node(_Node.code_development)
            self.add_quick_node(_Node.generate_git_diff)

            self.add_quick_edge(START, _Node.select_next_step)
            self.add_quick_edge(_Node.select_next_step, _Node.code_development)

            self.add_quick_conditional_edges(
                _Node.code_development, _select_next_or_end
            )

            self.add_quick_edge(_Node.generate_git_diff, END)
        elif IMPLEMENTATION_MODE == ImplementationModes.ALL_AT_ONCE:
            self.add_quick_node(_Node.develop_all_at_once)
            self.add_quick_node(_Node.generate_git_diff)

            self.add_quick_edge(START, _Node.develop_all_at_once)
            self.add_quick_edge(_Node.develop_all_at_once, _Node.generate_git_diff)
            self.add_quick_edge(_Node.generate_git_diff, END)
        else:
            raise ValueError(
                f"Invalid implementation mode: {IMPLEMENTATION_MODE}. "
                f"Expected one of: {ImplementationModes.__members__}"
            )

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
