from pathlib import Path

from deep_next.core.base_graph import BaseGraph, State
from deep_next.core.base_node import BaseNode
from deep_next.core.steps.action_plan import action_plan_graph
from deep_next.core.steps.action_plan.data_model import ActionPlan
from deep_next.core.steps.gather_project_knowledge.graph import (
    gather_project_knowledge_graph,
)
from deep_next.core.steps.implement.graph import implement_graph
from langgraph.graph import END, START


class DeepNextGraphState(State):

    # Input
    root_path: Path
    """Path to the root project directory."""

    problem_statement: str
    """The issue title and body."""

    hints: str
    """Comments made on the issue."""

    # Internal
    _project_knowledge: str
    """Project knowledge gathered from analyzing the repository structure and the source
     code."""

    _action_plan: ActionPlan | None
    """A list of files and the changes that need to be made to each of them."""

    # Output arguments
    git_diff: str
    """Final result of the graf flow: git diff of the changes made to the source code.
    """


class _Node(BaseNode):
    @staticmethod
    def gather_project_knowledge(state: DeepNextGraphState) -> dict:
        initial_state = gather_project_knowledge_graph.create_init_state(
            root_path=state["root_path"],
        )
        final_state = gather_project_knowledge_graph.compiled.invoke(initial_state)

        return {"_project_knowledge": final_state["project_knowledge"]}

    @staticmethod
    def create_action_plan(state: DeepNextGraphState) -> dict:
        action_plan: ActionPlan = action_plan_graph(
            root_path=state["root_path"],
            issue_statement=state["problem_statement"],
            project_knowledge=state["_project_knowledge"],
        )

        return {"_action_plan": action_plan}

    @staticmethod
    def implement(state: DeepNextGraphState) -> dict:
        initial_state = implement_graph.create_init_state(
            root_path=state["root_path"],
            issue_statement=state["problem_statement"],
            action_plan=state["_action_plan"],
        )
        final_state = implement_graph.compiled.invoke(initial_state)

        return {"git_diff": final_state["git_diff"]}


class DeepNextGraph(BaseGraph):
    def __init__(self):
        super().__init__(DeepNextGraphState)

    def _build(self):
        self.add_quick_node(_Node.gather_project_knowledge)
        self.add_node(_Node.create_action_plan)
        self.add_node(_Node.implement)

        self.add_quick_edge(START, _Node.gather_project_knowledge)
        self.add_quick_edge(_Node.gather_project_knowledge, _Node.create_action_plan)
        self.add_quick_edge(_Node.create_action_plan, _Node.implement)
        self.add_quick_edge(_Node.implement, END)

    def create_init_state(
        self, root: Path, problem_statement: str, hints: str
    ) -> DeepNextGraphState:
        return DeepNextGraphState(
            root_path=root,
            problem_statement=problem_statement,
            hints=hints,
            _project_knowledge="",
            _action_plan=None,
            git_diff="",
        )

    def __call__(self, *_, problem_statement: str, hints: str, root: Path) -> str:
        initial_state = self.create_init_state(
            root=root, problem_statement=problem_statement, hints=hints
        )
        final_state = self.compiled.invoke(initial_state)

        return final_state["git_diff"]


deep_next_graph = DeepNextGraph()


if __name__ == "__main__":
    print(f"Saved to: {deep_next_graph.visualize(subgraph_depth=3)}")
