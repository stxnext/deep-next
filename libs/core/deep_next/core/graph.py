from pathlib import Path

from deep_next.core.base_graph import BaseGraph
from deep_next.core.steps.action_plan import action_plan_graph
from deep_next.core.steps.action_plan.data_model import ActionPlan
from deep_next.core.steps.code_review.graph import code_review_graph
from deep_next.core.steps.gather_project_knowledge.graph import (
    gather_project_knowledge_graph,
)
from deep_next.core.steps.implement.graph import implement_graph
from langgraph.graph import END, START
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
    problem_statement: str = Field(description="The issue title and body.")
    hints: str = Field(description="Comments made on the issue.")

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
            issue_statement=state.problem_statement,
            project_knowledge=state.project_knowledge,
        )
        final_state = action_plan_graph.compiled.invoke(init_state)

        return {"action_plan": final_state["action_plan"]}

    @staticmethod
    def implement(state: _State) -> dict:
        init_state = implement_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.problem_statement,
            action_plan=state.action_plan,
        )
        final_state = implement_graph.compiled.invoke(init_state)

        return {"git_diff": final_state["git_diff"]}

    @staticmethod
    def review_code(state: _State) -> dict:
        initial_state = code_review_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.problem_statement,
            project_knowledge=state.project_knowledge,
            git_diff=state.git_diff,
        )
        final_state = code_review_graph.compiled.invoke(initial_state)

        return {"code_review_issues": final_state["result"]["issues"]}


class DeepNextGraph(BaseGraph):
    """Main graph for DeepNext."""

    def __init__(self):
        super().__init__(_State)

    def _build(self):
        self.add_quick_node(_Node.gather_project_knowledge)
        self.add_node(_Node.create_action_plan)
        self.add_node(_Node.implement)
        self.add_node(_Node.review_code)

        self.add_quick_edge(START, _Node.gather_project_knowledge)
        self.add_quick_edge(_Node.gather_project_knowledge, _Node.create_action_plan)
        self.add_quick_edge(_Node.create_action_plan, _Node.implement)
        self.add_quick_edge(_Node.implement, _Node.review_code)
        self.add_quick_edge(_Node.review_code, END)

    def create_init_state(
        self, root: Path, problem_statement: str, hints: str
    ) -> _State:
        return _State(
            root_path=root,
            problem_statement=problem_statement,
            hints=hints,
        )

    def __call__(
        self, *_, problem_statement: str, hints: str, root: Path
    ) -> DeepNextResult:
        initial_state = self.create_init_state(
            root=root, problem_statement=problem_statement, hints=hints
        )
        final_state = self.compiled.invoke(initial_state)

        state = _State.model_validate(final_state)

        ordered_steps_str = "\n".join(
            [
                (
                    f"{idx}. {step.title}\n\n"
                    f"{step.description}\n"
                    f"Target file: {step.target_file}\n"
                )
                for idx, step in enumerate(state.action_plan.ordered_steps, start=1)
            ]
        )

        return DeepNextResult(
            git_diff=state.git_diff,
            reasoning=state.action_plan.reasoning,
            action_plan=ordered_steps_str,
        )


deep_next_graph = DeepNextGraph()


if __name__ == "__main__":
    print(f"Saved to: {deep_next_graph.visualize(subgraph_depth=2)}")
