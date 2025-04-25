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


class _StateActionPlan(BaseModel):

    root_path: Path = Field(description="Path to the root project directory.")
    problem_statement: str = Field(description="The issue title and body.")
    hints: str = Field(description="Comments made on the issue.")

    project_knowledge: str | None = Field(default=None)
    action_plan: ActionPlan | None = Field(default=None)


class _StateImplement(BaseModel):

    root_path: Path = Field(description="Path to the root project directory.")
    action_plan: ActionPlan | None = Field(default=None)

    git_diff: str | None = Field(
        default=None,
        description="Final result: git diff of the changes made to the source code.",
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

    def __call__(self, *_, problem_statement: str, hints: str, root: Path) -> str:
        initial_state = self.create_init_state(
            root=root, problem_statement=problem_statement, hints=hints
        )
        final_state = self.compiled.invoke(initial_state)

        return _State.model_validate(final_state).git_diff


class DeepNextActionPlanGraph(BaseGraph):
    """
    Graph for the first phase of DeepNext.

    Gather the project knowledge and creating an action plan.
    """

    def __init__(self):
        super().__init__(_StateActionPlan)

    def _build(self):
        self.add_quick_node(_Node.gather_project_knowledge)
        self.add_node(_Node.create_action_plan)

        self.add_quick_edge(START, _Node.gather_project_knowledge)
        self.add_quick_edge(_Node.gather_project_knowledge, _Node.create_action_plan)
        self.add_quick_edge(_Node.create_action_plan, END)

    def create_init_state(
        self, root_path: Path, problem_statement: str, hints: str
    ) -> _StateActionPlan:
        return _StateActionPlan(
            root_path=root_path,
            problem_statement=problem_statement,
            hints=hints,
        )

    def __call__(
        self, *_, root_path: Path, problem_statement: str, hints: str
    ) -> ActionPlan:
        initial_state = self.create_init_state(
            root_path=root_path, problem_statement=problem_statement, hints=hints
        )
        final_state = self.compiled.invoke(initial_state)

        return _State.model_validate(final_state).action_plan


class DeepNextImplementGraph(BaseGraph):
    """
    Graph for the second phase of DeepNext.

    Implement the action plan and generate the git diff.
    """

    def __init__(self):
        super().__init__(_StateImplement)

    def _build(self):
        self.add_node(_Node.implement)

        self.add_quick_edge(START, _Node.implement)
        self.add_quick_edge(_Node.implement, END)

    def create_init_state(
        self,
        root_path: Path,
        action_plan: ActionPlan,
    ) -> _StateImplement:
        return _StateImplement(
            root_path=root_path,
            action_plan=action_plan,
        )

    def __call__(
        self,
        *_,
        root_path: Path,
        action_plan: ActionPlan,
    ) -> ActionPlan:
        initial_state = self.create_init_state(
            root_path=root_path,
            action_plan=action_plan,
        )
        final_state = self.compiled.invoke(initial_state)

        return _State.model_validate(final_state).action_plan


deep_next_action_plan_graph = DeepNextActionPlanGraph()
deep_next_implement_graph = DeepNextImplementGraph()
deep_next_graph = DeepNextGraph()


if __name__ == "__main__":
    print(f"Saved to: {deep_next_graph.visualize(subgraph_depth=2)}")
