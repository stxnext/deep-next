from pathlib import Path

from deep_next.core.base_graph import BaseGraph
from deep_next.core.io import read_txt
from deep_next.core.steps.code_review.run_review.code_reviewer import CodeReviewContext
from deep_next.core.steps.code_review.run_review.run_review import (
    ALL_CODE_REVIEWERS,
    run_reviewers,
)
from langgraph.graph import END, START
from pydantic import BaseModel, Field
from unidiff import PatchSet


class CodeReviewResult(BaseModel):
    issues: dict[str, list[str]] = Field(
        description="Code review issues found during the code review process.",
    )
    completed: dict[str, bool] = Field(
        description="Code review completed status for each file in the git diff.",
    )


class _State(BaseModel):
    # Input
    root_path: Path = Field(description="Path to the root project directory.")
    issue_statement: str = Field(description="The issue title and body.")
    project_knowledge: str = Field(
        description="Knowledge about the project, such as its structure and purpose."
    )
    git_diff: str = Field(
        description="Git diff of the changes made to the source code."
    )
    include_code_fragments: bool = Field(
        default=True,
    )

    code_fragments: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Code fragments selected from the files in the git diff.",
    )

    # Output
    result: CodeReviewResult | None = Field(
        default=None,
        description=(
            "Code review issues found during the code review process"
            " and potential errors."
        ),
    )


class _Node:
    @staticmethod
    def select_code(state: _State) -> dict:
        modified_files = {}
        for patch in PatchSet(state.git_diff):
            rel_path = Path(patch.path)
            abs_path = state.root_path / rel_path

            if not abs_path.is_file():
                raise FileNotFoundError(
                    f"Critical error - cannot resolve path based on git diff. "
                    f"File {rel_path} not found within {state.root_path}."
                )

            modified_files[str(rel_path)] = [read_txt(abs_path)]

        return {"code_fragments": modified_files}

    @staticmethod
    def review_code(state: _State) -> dict:
        review_result = run_reviewers(
            ALL_CODE_REVIEWERS,
            CodeReviewContext(
                root_path=state.root_path,
                issue_statement=state.issue_statement,
                project_knowledge=state.project_knowledge,
                git_diff=state.git_diff,
                code_fragments=state.code_fragments,
            ),
        )
        return {
            "result": {
                "issues": review_result.issues,
                "completed": review_result.review_completed,
            }
        }


class CodeReviewGraph(BaseGraph):
    """Implementation of "Develop Edits" step in LangGraph."""

    def __init__(self):
        super().__init__(_State)

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
        project_knowledge: str,
        git_diff: str,
        include_code_fragments: bool = True,
    ) -> _State:
        return _State(
            root_path=root_path,
            issue_statement=issue_statement,
            project_knowledge=project_knowledge,
            git_diff=git_diff,
            include_code_fragments=include_code_fragments,
        )

    def __call__(
        self,
        root_path: Path,
        issue_statement: str,
        project_knowledge: str,
        git_diff: str,
        include_code_fragments: bool = True,
    ) -> CodeReviewResult:
        initial_state = self.create_init_state(
            root_path,
            issue_statement,
            project_knowledge,
            git_diff,
            include_code_fragments,
        )
        final_state = self.compiled.invoke(initial_state)
        return CodeReviewResult.model_validate(final_state["result"])


code_review_graph = CodeReviewGraph()
