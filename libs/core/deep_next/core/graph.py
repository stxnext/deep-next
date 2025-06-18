import textwrap
from pathlib import Path
from typing import Literal

from deep_next.common.common import prepare_issue_statement
from deep_next.core.base_graph import BaseGraph
from deep_next.core.config import AUTOMATED_CODE_REVIEW_MAX_ATTEMPTS
from deep_next.core.steps.action_plan import action_plan_graph
from deep_next.core.steps.action_plan.data_model import ActionPlan, Step
from deep_next.core.steps.code_review.graph import code_review_graph
from deep_next.core.steps.gather_project_knowledge.graph import (
    gather_project_knowledge_graph,
)
from deep_next.core.steps.implement.graph import implement_graph
from langgraph.graph import END, START
from loguru import logger
from pydantic import BaseModel, Field


class DeepNextResult(BaseModel):
    """Response model for DeepNext."""

    git_diff: str = Field(
        description="Final result: git diff of the changes made to the source code."
    )
    reasoning: str = Field(description="Reasoning behind the changes made.")
    action_plan: str = Field(description="Action plan for the changes made.")


class _State(BaseModel):

    root_path: Path = Field(description="Path to the root project directory.")
    issue_title: str = Field(description="The issue title.")
    issue_description: str = Field(description="The issue description.")
    issue_comments: list[str] = Field(
        default_factory=list, description="Comments made on the issue."
    )

    project_knowledge: str | None = Field(default=None)
    action_plan: ActionPlan | None = Field(default=None)

    git_diff: str | None = Field(
        default=None,
        description="Final result: git diff of the changes made to the source code.",
    )

    code_review_issues: list[str] = Field(
        default_factory=list,
        description="Code review of the changes made to the source code.",
    )
    code_review_attempts: int = Field(
        default=0, description="Number of code review retry attempts."
    )

    @property
    def issue_statement(self) -> str:
        return prepare_issue_statement(
            issue_title=self.issue_title,
            issue_description=self.issue_description,
            issue_comments=self.issue_comments,
        )


class _Node:
    @staticmethod
    def gather_project_knowledge(state: _State) -> dict:
        init_state = gather_project_knowledge_graph.create_init_state(
            root_path=state.root_path,
        )
        final_state = gather_project_knowledge_graph.compiled.invoke(init_state)
        return {"project_knowledge": final_state["project_knowledge"]}

    @staticmethod
    def create_action_plan(state: _State) -> dict:
        init_state = action_plan_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.issue_statement,
            project_knowledge=state.project_knowledge,
        )
        final_state = action_plan_graph.compiled.invoke(init_state)

        return {"action_plan": final_state["action_plan"]}

    @staticmethod
    def implement(state: _State) -> dict:
        init_state = implement_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.issue_statement,
            action_plan=state.action_plan,
        )
        final_state = implement_graph.compiled.invoke(init_state)

        return {"git_diff": final_state["git_diff"]}

    @staticmethod
    def review_code(state: _State) -> dict:
        initial_state = code_review_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.issue_statement,
            project_knowledge=state.project_knowledge,
            git_diff=state.git_diff,
        )
        final_state = code_review_graph.compiled.invoke(initial_state)

        return {"code_review_issues": final_state["result"]["issues"]}

    @staticmethod
    def prepare_automated_code_review_changes(state: _State) -> _State:
        state.code_review_attempts += 1

        suggestions = "\n".join(state.code_review_issues)
        hints = textwrap.dedent(
            f"""\
            Problem statement now includes suggestions from an automated code review.
            These are possible improvements to the code based on best practices and
            common patterns.

            Analyse each suggestion carefully. Not all of them need to be applied —
            use your judgment.

            Here is the original issue for context:
            <original_issue_statement>
            {state.problem_statement}
            </original_issue_statement>
        """
        )

        new_state = _State(
            root_path=state.root_path,
            issue_title=state.issue_title,
            issue_description=f"[Auto Code Review Suggestions]:\n{suggestions}",
            issue_comments=[hints],
            code_review_attempts=state.code_review_attempts,
        )

        logger.debug(new_state.problem_statement)

        return new_state


def _apply_code_review_suggestions_or_end(
    state: _State,
) -> Literal[_Node.prepare_automated_code_review_changes.__name__, END]:
    if not state.code_review_issues:
        logger.success("No code review suggestions found. Code seems to be ok.")
        return END

    if state.code_review_attempts < AUTOMATED_CODE_REVIEW_MAX_ATTEMPTS:
        logger.debug(
            f"Found `{len(state.code_review_issues)}` issues. "
            f"Retry #{state.code_review_attempts + 1}"
        )
        return _Node.prepare_automated_code_review_changes.__name__

    logger.warning("Max code review attempts reached. Ending loop.")
    return END


class DeepNextGraph(BaseGraph):
    """Main graph for DeepNext."""

    def __init__(self):
        super().__init__(_State)

    def _build(self):
        self.add_quick_node(_Node.gather_project_knowledge)
        self.add_node(_Node.create_action_plan)
        self.add_node(_Node.implement)
        self.add_node(_Node.review_code)
        self.add_node(_Node.prepare_automated_code_review_changes)

        self.add_quick_edge(START, _Node.gather_project_knowledge)
        self.add_quick_edge(_Node.gather_project_knowledge, _Node.create_action_plan)
        self.add_quick_edge(_Node.create_action_plan, _Node.implement)

        self.add_quick_edge(_Node.implement, _Node.review_code)
        self.add_quick_edge(
            _Node.prepare_automated_code_review_changes, _Node.gather_project_knowledge
        )

        self.add_quick_conditional_edges(
            _Node.review_code, _apply_code_review_suggestions_or_end
        )

    def create_init_state(
        self,
        root: Path,
        issue_title: str,
        issue_description: str,
        issue_comments: list[str] = [],  # noqa
    ) -> _State:
        return _State(
            root_path=root,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_comments=issue_comments,
        )

    def _steps_to_str(self, steps: list[Step]):
        ordered_steps_strs = []

        for idx, step in enumerate(steps, start=1):

            target_files_str = "\n".join(
                [f"- {target_file}" for target_file in step.target_files]
            )

            ordered_steps_strs.append(
                f"{idx}. {step.title}\n\n"
                f"{step.description}\n\n"
                f"Target files:\n"
                f"{target_files_str}"
            )

        return "\n\n".join(ordered_steps_strs)

    def __call__(
        self,
        *_,
        issue_title: str,
        issue_description: str,
        issue_comments: list[str] = [],  # noqa
        root: Path,
    ) -> DeepNextResult:
        initial_state = self.create_init_state(
            root=root,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_comments=issue_comments,
        )
        final_state = self.compiled.invoke(initial_state)

        state = _State.model_validate(final_state)

        return DeepNextResult(
            git_diff=state.git_diff,
            reasoning=state.action_plan.reasoning,
            action_plan=self._steps_to_str(state.action_plan.ordered_steps),
        )


deep_next_graph = DeepNextGraph()


if __name__ == "__main__":
    print(f"Saved to: {deep_next_graph.visualize(subgraph_depth=2)}")
