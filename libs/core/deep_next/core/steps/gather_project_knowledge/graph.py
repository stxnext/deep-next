import textwrap
from pathlib import Path

from deep_next.core.base_graph import BaseGraph, State
from deep_next.core.base_node import BaseNode
from deep_next.core.steps.gather_project_knowledge.project_description import (
    create_project_description,
)
from deep_next.core.steps.gather_project_knowledge.project_map import tree
from langgraph.constants import START
from langgraph.graph import END


class GatherProjectKnowledgeGraphState(State):
    # Input
    root_path: Path

    # Internal
    _project_description: str
    _project_map: str

    # Output
    project_knowledge: str


class _Node(BaseNode):
    @staticmethod
    def create_project_map(state: GatherProjectKnowledgeGraphState) -> dict:
        project_map = tree(path=state["root_path"])

        return {"_project_map": project_map}

    @staticmethod
    def create_project_description(
        state: GatherProjectKnowledgeGraphState,
    ) -> dict:
        project_description = create_project_description(root_path=state["root_path"])

        return {
            "_project_description": project_description,
        }

    @staticmethod
    def parse_final_state(state: GatherProjectKnowledgeGraphState) -> dict:
        project_knowledge_tmpl = textwrap.dedent(
            """\
            PROJECT_DESCRIPTION
            --------------------
            {project_description}
            --------------------

            PROJECT_MAP
            --------------------
            {project_map}
            --------------------
            """
        )
        project_knowledge = project_knowledge_tmpl.format(
            project_description=state["_project_description"],
            project_map=state["_project_map"],
        )

        return {"project_knowledge": project_knowledge}


class GatherProjectKnowledgeGraph(BaseGraph):
    """Implementation of "Gather Project Knowledge" step in LangGraph"""

    def __init__(self):
        super().__init__(GatherProjectKnowledgeGraphState)

    def _build(self) -> None:
        # Nodes
        self.add_quick_node(_Node.create_project_map)
        self.add_quick_node(_Node.create_project_description)
        self.add_quick_node(_Node.parse_final_state)

        # Edges
        self.add_quick_edge(START, _Node.create_project_map)
        self.add_quick_edge(START, _Node.create_project_description)
        self.add_quick_edge(_Node.create_project_map, _Node.parse_final_state)
        self.add_quick_edge(_Node.create_project_description, _Node.parse_final_state)
        self.add_quick_edge(_Node.parse_final_state, END)

    def create_init_state(self, root_path: Path) -> GatherProjectKnowledgeGraphState:
        return GatherProjectKnowledgeGraphState(
            root_path=root_path,
            _project_description="<MISSING>",
            _project_map="<MISSING>",
            project_knowledge="<MISSING>",
        )

    def __call__(self, root_path: Path) -> str:
        init_state = self.create_init_state(root_path)
        state: GatherProjectKnowledgeGraphState = self.compiled.invoke(init_state)
        return state["project_knowledge"]


gather_project_knowledge_graph = GatherProjectKnowledgeGraph()


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv
    from deep_next.common.config import MONOREPO_ROOT_PATH

    load_monorepo_dotenv()

    path = gather_project_knowledge_graph.visualize()
    print(f"Saved to: {path}")

    print(gather_project_knowledge_graph(MONOREPO_ROOT_PATH))
