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


class _StateActionPlan(BaseModel):

    root_path: Path = Field(description="Path to the root project directory.")
    problem_statement: str = Field(description="The issue title and body.")
    hints: str = Field(description="Comments made on the issue.")

    project_knowledge: str | None = Field(default=None)
    action_plan: ActionPlan | None = Field(default=None)


class _StateImplement(BaseModel):

    root_path: Path = Field(description="Path to the root project directory.")
    problem_statement: str = Field(description="Problem statement.")
    action_plan: ActionPlan | None = Field(default=None)

    git_diff: str | None = Field(
        default=None,
        description="Final result: git diff of the changes made to the source code.",
    )


class _NodeActionPlan:
    @staticmethod
    def gather_project_knowledge(state: _StateActionPlan) -> dict:
        init_state = gather_project_knowledge_graph.create_init_state(
            root_path=state.root_path,
        )
        final_state = gather_project_knowledge_graph.compiled.invoke(init_state)
        return {"project_knowledge": final_state["project_knowledge"]}

    @staticmethod
    def create_action_plan(state: _StateActionPlan) -> dict:
        init_state = action_plan_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.problem_statement,
            project_knowledge=state.project_knowledge,
        )
        final_state = action_plan_graph.compiled.invoke(init_state)

        return {"action_plan": final_state["action_plan"]}


class _NodeImplement:
    @staticmethod
    def implement(state: _StateImplement) -> dict:
        init_state = implement_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.problem_statement,
            action_plan=state.action_plan,
        )
        final_state = implement_graph.compiled.invoke(init_state)

        return {"git_diff": final_state["git_diff"]}

    @staticmethod
    def review_code(state: _StateImplement) -> dict:
        initial_state = code_review_graph.create_init_state(
            root_path=state.root_path,
            issue_statement=state.problem_statement,
            project_knowledge=state.project_knowledge,
            git_diff=state.git_diff,
        )
        final_state = code_review_graph.compiled.invoke(initial_state)

        return {"code_review_issues": final_state["result"]["issues"]}


class DeepNextActionPlanGraph(BaseGraph):
    """
    Graph for the first phase of DeepNext.

    Gather the project knowledge and creating an action plan.
    """

    def __init__(self):
        super().__init__(_StateActionPlan)

    def _build(self):
        self.add_quick_node(_NodeActionPlan.gather_project_knowledge)
        self.add_node(_NodeActionPlan.create_action_plan)

        self.add_quick_edge(START, _NodeActionPlan.gather_project_knowledge)
        self.add_quick_edge(_NodeActionPlan.gather_project_knowledge, _NodeActionPlan.create_action_plan)
        self.add_quick_edge(_NodeActionPlan.create_action_plan, END)

    def create_init_state(
        self, root_path: Path, problem_statement: str, hints: str = ""
    ) -> _StateActionPlan:
        return _StateActionPlan(
            root_path=root_path,
            problem_statement=problem_statement,
            hints=hints,
        )

    def __call__(
        self, *_, root_path: Path, problem_statement: str, hints: str = ""
    ) -> ActionPlan:
        initial_state = self.create_init_state(
            root_path=root_path, problem_statement=problem_statement, hints=hints
        )
        final_state = self.compiled.invoke(initial_state)

        return _StateImplement.model_validate(final_state).action_plan


class DeepNextImplementGraph(BaseGraph):
    """
    Graph for the second phase of DeepNext.

    Implement the action plan and generate the git diff.
    """

    def __init__(self):
        super().__init__(_StateImplement)

    def _build(self):
        self.add_node(_NodeImplement.implement)

        self.add_quick_edge(START, _NodeImplement.implement)
        self.add_quick_edge(_NodeImplement.implement, END)

    def create_init_state(
        self,
        root_path: Path,
        problem_statement: str,
        action_plan: ActionPlan,
    ) -> _StateImplement:
        return _StateImplement(
            root_path=root_path,
            problem_statement=problem_statement,
            action_plan=action_plan,
        )

    def __call__(
        self,
        *_,
        root_path: Path,
        problem_statement: str,
        action_plan: ActionPlan,
    ) -> str:
        initial_state = self.create_init_state(
            root_path=root_path,
            problem_statement=problem_statement,
            action_plan=action_plan,
        )
        final_state = self.compiled.invoke(initial_state)

        return _StateImplement.model_validate(final_state).git_diff


deep_next_action_plan_graph = DeepNextActionPlanGraph()
deep_next_implement_graph = DeepNextImplementGraph()
