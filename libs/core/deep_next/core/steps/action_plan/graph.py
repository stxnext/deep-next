from pathlib import Path

from deep_next.core.base_graph import BaseGraph
from deep_next.core.base_node import BaseNode
from deep_next.core.config import SRFConfig
from deep_next.core.io import read_txt
from deep_next.core.steps.action_plan.action_plan import create_action_plan
from deep_next.core.steps.action_plan.data_model import (
    ActionPlan,
    ExistingCodeContext,
    FileCodeContext,
)
from deep_next.core.steps.action_plan.srf import srf_graph
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import END
from pydantic import BaseModel, Field


class _State(BaseModel):
    # 🔹 Input
    root_path: Path = Field(description="Root path for the project.")
    issue_statement: str = Field(description="Issue details")
    project_knowledge: str = Field(description="Relevant project knowledge.")

    # 🔸 Internal (Hidden)
    code_context: ExistingCodeContext = Field(
        default_factory=list, description="Files related to the issue."
    )

    # 🔹 Output
    action_plan: ActionPlan | None = Field(
        default=None, description="Finalized detailed design modifications."
    )


class _Node:
    @staticmethod
    def define_code_context(state: _State) -> dict:
        initial_state = srf_graph.create_init_state(
            query=state.issue_statement,
            root_path=state.root_path,
        )
        final_state = srf_graph.compiled.invoke(
            initial_state,
            config=RunnableConfig(recursion_limit=SRFConfig.CYCLE_ITERATION_LIMIT),
        )

        # TODO: Add explanation! Code context should be returned from `srf_graph`.
        code_context = [
            FileCodeContext(
                path=path,
                code_snippet=read_txt(path),
                explanation="<missing explanation>",
            )
            for path in final_state["final_results"]
        ]

        return {"code_context": ExistingCodeContext(code_context=code_context)}

    @staticmethod
    def create_action_plan(state: _State) -> dict:
        action_plan: ActionPlan = create_action_plan(
            root_path=state.root_path,
            issue_statement=state.issue_statement,
            existing_code_context=state.code_context,
            project_knowledge=state.project_knowledge,
        )

        return {"action_plan": action_plan}


class ActionPlanGraph(BaseGraph):
    def __init__(self):
        super().__init__(_State)

    def __call__(
        self, root_path: Path, issue_statement: str, project_knowledge: str
    ) -> ActionPlan:
        initial_state = _State(
            root_path=root_path,
            issue_statement=issue_statement,
            project_knowledge=project_knowledge,
        )
        final_state = self.compiled.invoke(initial_state)

        return final_state["action_plan"]

    def _build(self) -> None:
        # Nodes
        self.add_quick_node(_Node.define_code_context)
        self.add_quick_node(_Node.create_action_plan)

        # Edges
        self.add_quick_edge(START, _Node.define_code_context)
        self.add_quick_edge(_Node.define_code_context, _Node.create_action_plan)
        self.add_quick_edge(_Node.create_action_plan, END)

    def create_init_state(self, *args, **kwargs) -> _State:
        raise NotImplementedError(
            "Probably not important since pydantic BaseModel is used for state."
        )


graph = ActionPlanGraph()


if __name__ == "__main__":
    print(f"Saved to: {graph.visualize()}")

    from deep_next.common.common import load_monorepo_dotenv
    from deep_next.core.config import ROOT_DIR
    from deep_next.core.steps.gather_project_knowledge.graph import (
        gather_project_knowledge_graph,
    )

    load_monorepo_dotenv()

    root_path = Path(ROOT_DIR / "tests" / "_resources" / "example_project")
    action_plan = graph(
        root_path=root_path,
        issue_statement="Add proper type hints to the project.",
        project_knowledge=gather_project_knowledge_graph(root_path=root_path),
    )
    print(action_plan)
