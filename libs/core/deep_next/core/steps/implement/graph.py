from copy import copy
from pathlib import Path
from typing import Literal

import tenacity
from deep_next.core.base_graph import BaseGraph, State
from deep_next.core.base_node import BaseNode
from deep_next.core.steps.action_plan.data_model import ActionPlan, Step
from deep_next.core.steps.implement.apply_patch.apply_patch import apply_patch
from deep_next.core.steps.implement.apply_patch.common import ApplyPatchError
from deep_next.core.steps.implement.develop_patch import (
    ParsePatchesError,
    develop_single_file_patches,
    parse_patches,
)
from deep_next.core.steps.implement.git_diff import generate_diff
from deep_next.core.steps.implement.utils import CodePatch
from langgraph.graph import END, START


class ImplementationGraphState(State):
    # Input
    root_path: Path
    issue_statement: str
    steps: list[Step]

    # Internal
    _steps_remaining: list[Step]
    _selected_step: Step | None

    # Output
    git_diff: str


class _Node(BaseNode):
    @staticmethod
    def select_next_step(state: ImplementationGraphState) -> dict:
        step: Step = state["_steps_remaining"].pop(0)

        return {"_selected_step": step}

    @staticmethod
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        retry=tenacity.retry_if_exception_type((ApplyPatchError, ParsePatchesError)),
        reraise=True,
    )
    def code_development(
        state: ImplementationGraphState,
    ) -> ImplementationGraphState:
        step = state["_selected_step"]

        raw_patches = develop_single_file_patches(step, state["issue_statement"])

        patches: list[CodePatch] = parse_patches(raw_patches)
        patches = [patch for patch in patches if patch.before != patch.after]

        for patch in patches:
            apply_patch(patch)

        return state

    @staticmethod
    def generate_git_diff(state: ImplementationGraphState) -> dict:
        return {"git_diff": generate_diff(state["root_path"])}


def _select_next_or_end(
    state: ImplementationGraphState,
) -> Literal[_Node.select_next_step.__name__, _Node.generate_git_diff.__name__]:
    return (
        _Node.select_next_step.__name__
        if state["_steps_remaining"]
        else _Node.generate_git_diff.__name__
    )


class ImplementGraph(BaseGraph):
    """Implementation of "Implement" step in LangGraph."""

    def __init__(self):
        super().__init__(ImplementationGraphState)

    def _build(self) -> None:
        # Nodes
        self.add_quick_node(_Node.select_next_step)
        self.add_quick_node(_Node.code_development)
        self.add_quick_node(_Node.generate_git_diff)

        # Edges
        self.add_quick_edge(START, _Node.select_next_step)
        self.add_quick_edge(_Node.select_next_step, _Node.code_development)
        self.add_quick_edge(_Node.generate_git_diff, END)

        # Conditional Edges
        self.add_quick_conditional_edges(_Node.code_development, _select_next_or_end)

    def create_init_state(
        self, root_path: Path, issue_statement: str, action_plan: ActionPlan
    ) -> ImplementationGraphState:
        return ImplementationGraphState(
            root_path=root_path,
            issue_statement=issue_statement,
            steps=action_plan.ordered_steps,
            _steps_remaining=copy(action_plan.ordered_steps),
            _selected_step=None,
            git_diff="",
        )

    def __call__(
        self, root_path: Path, issue_statement: str, action_plan: ActionPlan
    ) -> str:
        initial_state = self.create_init_state(root_path, issue_statement, action_plan)
        final_state: ImplementationGraphState = self.compiled.invoke(initial_state)

        return final_state["git_diff"]


implement_graph = ImplementGraph()
