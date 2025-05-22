import operator
from pathlib import Path
from typing import Annotated, TypedDict

import tenacity
from deep_next.core.base_graph import BaseGraph
from deep_next.core.config import SRFConfig
from deep_next.core.steps.action_plan.srf.file_selection.analysis_model import (
    RelevantFile,
)
from deep_next.core.steps.action_plan.srf.file_selection.graph import (
    file_selection_graph,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.tools import (
    dispose_tools,
    init_tools,
)
from langchain.schema.output_parser import OutputParserException
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import END
from loguru import logger

PROJECT_FILES_TREE_NO_EXCLUSION_MSG = "---NO-EXCLUSION---"


class SRFError(Exception):
    """Raised when SRF fails to find any relevant files."""


class _State(TypedDict):
    # Input
    root_path: Path
    query: str

    # Internal
    _cycle_results: Annotated[list[RelevantFile], operator.add]
    _cycle_invalid_results: Annotated[list[RelevantFile], operator.add]
    _cycle_iterations: Annotated[list[int], operator.add]

    # Output
    final_results: list[RelevantFile]
    final_invalid_results: list[RelevantFile]


def setup_search_tools(state: _State) -> None:
    init_tools(state["root_path"])


def cleanup_search_tools(state: _State) -> None:
    dispose_tools(state["root_path"])


class _Node:
    @staticmethod
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type((OutputParserException, ValueError)),
        reraise=True,
    )
    def single_file_selection_cycle(state: _State) -> dict:
        """
        Run a single cycle of file selection.

        This function is called multiple times in
        the SRF process and the unique results are combined at the end for lower
        variance.
        """
        logger.debug("Running single file selection cycle")

        init_state = file_selection_graph.create_init_state(
            query=state["query"],
            root_path=state["root_path"],
        )
        try:
            result = file_selection_graph.compiled.invoke(
                init_state,
                config=RunnableConfig(recursion_limit=SRFConfig.CYCLE_ITERATION_LIMIT),
            )
        except Exception as e:
            logger.error(f"Error during file selection cycle: {e}")
            result = {
                "relevant_files": [],
                "invalid_files": [],
                "_iteration_count": 0,
            }

        return {
            "_cycle_results": result["relevant_files"],
            "_cycle_invalid_results": result["invalid_files"],
            "_cycle_iterations": [result["_iteration_count"]],
        }

    @staticmethod
    def combine_results(state: _State) -> dict:
        combined_results = set(state["_cycle_results"])
        combined_invalid_results = set(state["_cycle_invalid_results"])

        if len(combined_results) == 0:
            raise SRFError(
                (
                    "SRF failed to find any relevant files. This is "
                    " very disturbing. Double check logs and query to spot the cause. "
                    "Relevant files are required for DeepNext to proceed."
                )
            )
        return {
            "final_results": list(combined_results),
            "final_invalid_results": list(combined_invalid_results),
        }


class SelectRelatedFilesGraph(BaseGraph):
    def __init__(self, n_cycles: int | None = None):
        self.n_cycles = n_cycles or SRFConfig.N_CYCLES

        super().__init__(_State)

    def _add_independent_file_selection_nodes(self) -> None:
        for i in range(self.n_cycles):
            self.add_node(
                f"{_Node.single_file_selection_cycle.__name__} {i + 1}",
                _Node.single_file_selection_cycle,
            )

    def _add_independent_file_selection_nodes_edges(self, to_node) -> None:
        for i in range(self.n_cycles):
            self.add_quick_edge(
                START,
                f"{_Node.single_file_selection_cycle.__name__} {i + 1}",
            )
            self.add_quick_edge(
                f"{_Node.single_file_selection_cycle.__name__} {i + 1}",
                to_node,
            )

    def _build(self):
        self._add_independent_file_selection_nodes()
        self.add_quick_node(_Node.combine_results)

        self.set_setup_fn(setup_search_tools)
        self.set_teardown_fn(cleanup_search_tools)

        self._add_independent_file_selection_nodes_edges(_Node.combine_results)
        self.add_quick_edge(_Node.combine_results, END)

    def create_init_state(
        self,
        query: str,
        root_path: Path,
    ) -> _State:
        return _State(
            root_path=root_path,
            query=query,
            _cycle_results=[],
            _cycle_invalid_results=[],
            _cycle_iterations=[],
            final_results=[],
            final_invalid_results=[],
        )

    def __call__(
        self,
        query: str,
        root_path: Path,
    ) -> tuple[list[RelevantFile], list[RelevantFile], list[int]]:
        initial_state = self.create_init_state(
            root_path=root_path,
            query=query,
        )

        resp: _State = self.compiled.invoke(initial_state)

        return (
            resp["final_results"],
            resp["final_invalid_results"],
            resp["_cycle_iterations"],
        )


select_related_files_graph = SelectRelatedFilesGraph()


if __name__ == "__main__":
    print(f"Saved to: {select_related_files_graph.visualize()}")
