from collections import defaultdict
from pathlib import Path

from deep_next.common.common import load_monorepo_dotenv
from deep_next.core.base_graph import BaseGraph, State
from deep_next.core.base_node import BaseNode
from deep_next.core.steps.action_plan.srs.common_agentless import create_structure
from deep_next.core.steps.action_plan.srs.graph import select_related_snippets_graph
from deep_next.core.steps.code_review.review_code import review_code as _review_code
from langgraph.graph import END, START
from unidiff import PatchSet


class CodeReviewGraphState(State):
    # Input
    root_path: Path
    issue_statement: str
    git_diff: str
    include_code_fragments: bool

    _code_fragments: dict[str, list[str]]

    # Output
    code_review_issues: list[(str, str)]
    code_review_completed: dict[str, bool]


class _Node(BaseNode):

    # TODO: try to include all files from SRF here + the reasons they were selected.
    @staticmethod
    def select_code(state: CodeReviewGraphState) -> dict:
        if not state["include_code_fragments"]:
            return {"_code_fragments": {}}

        file_locations = select_related_snippets_graph(
            problem_statement=state["issue_statement"],
            root_path=state["root_path"],
            files=[patch.path for patch in PatchSet(state["git_diff"])],
            structure=create_structure(state["root_path"]),
        )

        _code_fragments = defaultdict(list)
        for file_name, locations in file_locations.items():
            for location in locations:
                file_lines = (state["root_path"] / file_name).read_text().splitlines()
                selected_lines = file_lines[location[0] : location[1]]

                selected_lines = [
                    f"{i + 1:4} |{line}"
                    for i, line in enumerate(selected_lines, start=location[0])
                ]

                _code_fragments[file_name].append("\n".join(selected_lines))

        return {"_code_fragments": _code_fragments}

    @staticmethod
    def review_code(state: CodeReviewGraphState) -> dict:
        code_review_issues, code_review_completed = _review_code(
            state["issue_statement"], state["git_diff"], state["_code_fragments"]
        )
        return {
            "code_review_issues": code_review_issues,
            "code_review_completed": code_review_completed,
        }


class CodeReviewGraph(BaseGraph):
    """Implementation of "Develop Edits" step in LangGraph."""

    def __init__(self):
        super().__init__(CodeReviewGraphState)

    def _build(self) -> None:
        # Nodes
        self.add_quick_node(_Node.select_code)
        self.add_quick_node(_Node.review_code)

        # Edges
        self.add_quick_edge(START, _Node.select_code)
        self.add_quick_edge(_Node.select_code, _Node.review_code)
        self.add_quick_edge(_Node.review_code, END)

    def create_init_state(
        self,
        root_path: Path,
        issue_statement: str,
        git_diff: str,
        include_code_fragments: bool = True,
    ) -> CodeReviewGraphState:
        return CodeReviewGraphState(
            root_path=root_path,
            issue_statement=issue_statement,
            git_diff=git_diff,
            include_code_fragments=include_code_fragments,
            _code_fragments={},
            code_review_issues=[],
            code_review_completed={},
        )

    def __call__(
        self,
        root_path: Path,
        issue_statement: str,
        git_diff: str,
        include_code_fragments: bool = True,
    ) -> tuple[list[(str, str)], dict[str, bool]]:
        initial_state = self.create_init_state(
            root_path, issue_statement, git_diff, include_code_fragments
        )
        final_state = self.compiled.invoke(initial_state)

        return final_state["code_review_issues"], final_state["code_review_completed"]


code_review_graph = CodeReviewGraph()

