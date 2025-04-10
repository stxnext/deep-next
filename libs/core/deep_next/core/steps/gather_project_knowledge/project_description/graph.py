from pathlib import Path

from deep_next.core.base_graph import BaseGraph, State
from deep_next.core.base_node import BaseNode
from deep_next.core.project_info import ProjectInfo, get_project_info
from deep_next.core.steps.action_plan.srf.graph import SelectRelatedFilesGraph
from deep_next.core.steps.gather_project_knowledge.project_description.generate_project_description import (  # noqa: E501
    generate_project_description,
)
from deep_next.core.steps.gather_project_knowledge.project_description.generate_questions import (  # noqa: E501
    generate_questions,
)
from deep_next.core.steps.gather_project_knowledge.project_map import tree
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import END


class GatherProjectDescriptionGraphState(State):
    # Input
    root_path: Path

    # Internal
    _questions: str
    _related_files: list[Path]
    _project_info: ProjectInfo

    # Output
    project_description_output: str


class _Node(BaseNode):
    @staticmethod
    def generate_questions(state: GatherProjectDescriptionGraphState) -> dict:
        project_tree = tree(path=state["root_path"])

        questions = generate_questions(
            repository_tree=project_tree,
            project_info=state["_project_info"],
        )

        print(questions.dump())
        return {
            "_questions": questions.dump(),
        }

    @staticmethod
    def get_srf_context(
        state: GatherProjectDescriptionGraphState,
    ) -> dict:
        srf_graph = SelectRelatedFilesGraph(n_cycles=1)
        initial_state = srf_graph.create_init_state(
            root_path=state["root_path"],
            query=state["_questions"],
        )
        final_srf_state = srf_graph.compiled.invoke(
            initial_state,
            config=RunnableConfig(recursion_limit=10),
        )

        return {
            "_related_files": final_srf_state["final_results"],
        }

    @staticmethod
    def project_description(state: GatherProjectDescriptionGraphState) -> dict:
        project_description = generate_project_description(
            questions=state["_questions"],
            related_files=state["_related_files"],
            repository_tree=tree(path=state["root_path"]),
            project_info=state["_project_info"],
        )

        return {"project_description": project_description}


class GatherProjectKnowledgeGraph(BaseGraph):
    """Implementation of "Gather Project Knowledge" step in LangGraph"""

    def __init__(self):
        super().__init__(GatherProjectDescriptionGraphState)

    def _build(self) -> None:
        # Nodes
        self.add_quick_node(_Node.generate_questions)
        self.add_quick_node(_Node.get_srf_context)
        self.add_quick_node(_Node.project_description)

        # Edges
        self.add_quick_edge(START, _Node.generate_questions)
        self.add_quick_edge(_Node.generate_questions, _Node.get_srf_context)
        self.add_quick_edge(_Node.get_srf_context, _Node.project_description)
        self.add_quick_edge(_Node.project_description, END)

    def create_init_state(self, root_path: Path) -> GatherProjectDescriptionGraphState:
        return GatherProjectDescriptionGraphState(
            root_path=root_path,
            _questions="<MISSING>",
            _related_files=[Path("<MISSING>")],
            _project_info=get_project_info(root_path),
            project_description_output="<MISSING>",
        )

    def __call__(self, root_path: Path) -> str:
        init_state = self.create_init_state(root_path)
        state = self.compiled.invoke(init_state)
        return state["project_description_output"]


gather_project_description_graph = GatherProjectKnowledgeGraph()


# if __name__ == "__main__":
#     from dotenv import load_dotenv

#     assert load_dotenv(ROOT_DIR / ".env")

#     path = gather_project_description_graph.visualize()
#     print(f"Saved to: {path}")

#     print(gather_project_description_graph(ROOT_DIR, "problem_statement"))
