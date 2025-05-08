from pathlib import Path

from deep_next.core.base_graph import BaseGraph
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
from pydantic import BaseModel


class _State(BaseModel):
    # Input
    root_path: Path

    # Internal
    questions: str
    related_files: list[Path]
    project_info: ProjectInfo

    # Output
    project_description_output: str


class _Node:
    @staticmethod
    def generate_questions(state: _State) -> dict:
        project_tree = tree(path=state.root_path)

        questions = generate_questions(
            repository_tree=project_tree,
            project_info=state.project_info,
        )

        print(questions.dump())
        return {
            "questions": questions.dump(),
        }

    @staticmethod
    def get_srf_context(
        state: _State,
    ) -> dict:
        srf_graph = SelectRelatedFilesGraph(n_cycles=1)
        initial_state = srf_graph.create_init_state(
            root_path=state.root_path,
            query=state.questions,
        )
        final_srf_state = srf_graph.compiled.invoke(
            initial_state,
            config=RunnableConfig(recursion_limit=10),
        )

        return {
            "related_files": [
                Path(result.path) for result in final_srf_state["final_results"]
            ],
        }

    @staticmethod
    def project_description(state: _State) -> dict:
        project_description = generate_project_description(
            questions=state.questions,
            related_files=state.related_files,
            repository_tree=tree(path=state.root_path),
            project_info=state.project_info,
        )

        return {"project_description_output": project_description}


class GatherProjectKnowledgeGraph(BaseGraph):
    """Implementation of "Gather Project Knowledge" step in LangGraph"""

    def __init__(self):
        super().__init__(_State)

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

    def create_init_state(self, root_path: Path) -> _State:
        return _State(
            root_path=root_path,
            questions="<MISSING>",
            related_files=[Path("<MISSING>")],
            project_info=get_project_info(root_path),
            project_description_output="<MISSING>",
        )

    def __call__(self, root_path: Path) -> str:
        init_state = self.create_init_state(root_path)
        state = self.compiled.invoke(init_state)
        return state["project_description_output"]


gather_project_description_graph = GatherProjectKnowledgeGraph()


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    path = gather_project_description_graph.visualize()
    print(f"Saved to: {path}")
