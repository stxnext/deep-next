import textwrap
from pathlib import Path

from deep_next.core.base_graph import BaseGraph
from deep_next.core.steps.gather_project_knowledge.project_description import (
    gather_project_description_graph,
)
from deep_next.core.steps.gather_project_knowledge.project_map import tree
from langgraph.constants import START
from langgraph.graph import END
from pydantic import BaseModel, Field


class _State(BaseModel):
    root_path: Path = Field(description="Path to the root project directory.")
    project_description: str | None = Field(
        default=None,
        description="Natural language summary of the project structure and purpose.",
    )
    project_map: str | None = Field(
        default=None,
        description="Map of source code - fs tree view.",
    )
    project_knowledge: str | None = Field(
        default=None, description="Structured representation of project knowledge."
    )


class _Node:
    @staticmethod
    def create_project_map(state: _State) -> dict:
        project_map = tree(path=state.root_path)

        return {"project_map": project_map}

    @staticmethod
    def create_project_description(state: _State) -> dict:
        project_description = gather_project_description_graph(
            root_path=state.root_path
        )

        return {"project_description": project_description.to_str()}

    @staticmethod
    def parse_final_state(state: _State) -> dict:
        project_knowledge_tmpl = textwrap.dedent(
            """
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
            project_description=state.project_description,
            project_map=state.project_map,
        )

        return {"project_knowledge": project_knowledge}


class GatherProjectKnowledgeGraph(BaseGraph):
    """Graph to gather project knowledge."""

    def __init__(self):
        super().__init__(_State)

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

    def create_init_state(self, root_path: Path) -> _State:
        return _State(
            root_path=root_path,
        )

    def __call__(self, root_path: Path) -> str:
        init_state = self.create_init_state(root_path)
        state: _State = self.compiled.invoke(init_state)

        return _State.model_validate(state).project_knowledge


gather_project_knowledge_graph = GatherProjectKnowledgeGraph()


if __name__ == "__main__":
    print(f"Saved to: {gather_project_knowledge_graph.visualize(subgraph_depth=3)}")
