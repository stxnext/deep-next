from pathlib import Path
from typing import Annotated, TypedDict

from deep_next.core.base_graph import BaseGraph
from deep_next.core.base_node import BaseNode
from deep_next.core.config import SRSConfig
from deep_next.core.steps.action_plan.srs._agentless import (
    create_structure,
    transfer_arb_locs_to_locs,
)
from deep_next.core.steps.action_plan.srs.localize_function import (
    localize_function_from_compressed_files,
)
from deep_next.core.steps.action_plan.srs.localize_lines import (
    localize_line_from_coarse_function_locs,
)
from langgraph.constants import START
from langgraph.graph import END


def _operator_merge_values_of_dict(
    state: dict[str, str], new_values: dict[str, str]
) -> dict[str, str]:
    """Merge values of a dict with new values.

    If the key is not in the state, add it. If it is, merge the values
    by splitting them by new line and removing duplicates.

    Example:
    state = {"a/a.py": "1\n2", "b/b.py": "3"}
    new_values = {"a/a.pu": "2\n3"}
    state = _operator_merge_values_of_dict(state, new_values)
    state = {"a/a.py": "1\n2\n3", "b/b.py": "3"}
    """
    for key, value in new_values.items():
        if key not in state:
            state[key] = value
        else:
            combined_values = state[key].split("\n") + value.split("\n")
            state[key] = "\n".join(set(combined_values))

    return state


class _State(TypedDict):
    # Input
    problem_statement: str
    files: list[Path]
    structure: dict

    # Internal
    _localized_functions: Annotated[dict[str, str], _operator_merge_values_of_dict]
    """A dict mapping file names to names of localized classes, methods, functions."""
    _localized_classes_functions_lines: Annotated[
        dict[str, str], _operator_merge_values_of_dict
    ]
    """A dict mapping file names to names of localized classes, methods, functions
    and lines. It is a more constrained version of `_localized_functions`."""

    # Output
    final_results: dict[str, list[list[int]]]
    """A dict mapping file names to specific lines in the file."""


class _Node(BaseNode):
    @staticmethod
    def localize_function(state: _State) -> dict:
        """Localize the function in the given file."""
        localized_functions = localize_function_from_compressed_files(
            state["files"], state["structure"], state["problem_statement"]
        )

        return {"_localized_functions": localized_functions}

    @staticmethod
    def localize_lines(state: _State) -> dict:
        localized_classes_functions = localize_line_from_coarse_function_locs(
            file_names=state["files"],
            coarse_locs=state["_localized_functions"],
            structure=state["structure"],
            problem_statement=state["problem_statement"],
        )

        return {
            "_localized_classes_functions_lines": localized_classes_functions,
        }

    @staticmethod
    def combine_results(state: _State) -> dict:
        localized_classes_functions = state["_localized_classes_functions_lines"]
        structure = state["structure"]

        transferred_locs_dict = {}
        for pred_file, locs in localized_classes_functions.items():
            (exact_location, merged_locations_with_padding) = transfer_arb_locs_to_locs(
                locs=locs,
                structure=structure,
                pred_file=pred_file,
                context_window=SRSConfig.CONTEXT_WINDOW,
            )

            transferred_locs_dict[pred_file] = merged_locations_with_padding

        return {
            "final_results": transferred_locs_dict,
        }


class SelectRelatedSnippetsGraph(BaseGraph):
    def __init__(self):
        super().__init__(_State)

    def _add_independent_snippets_selection_nodes(self) -> None:
        for i in range(SRSConfig.N_CYCLES):
            self.add_node(
                f"{_Node.localize_function.__name__} {i + 1}",
                _Node.localize_function,
            )
            self.add_node(
                f"{_Node.localize_lines.__name__} {i + 1}",
                _Node.localize_lines,
            )

    def _add_independent_snippets_selection_nodes_edges(self, to_node) -> None:
        for i in range(SRSConfig.N_CYCLES):
            self.add_quick_edge(
                START,
                f"{_Node.localize_function.__name__} {i + 1}",
            )
            self.add_quick_edge(
                f"{_Node.localize_function.__name__} {i + 1}",
                f"{_Node.localize_lines.__name__} {i + 1}",
            )
            self.add_quick_edge(
                f"{_Node.localize_lines.__name__} {i + 1}",
                to_node,
            )

    def _build(self):
        # Nodes
        self._add_independent_snippets_selection_nodes()
        self.add_quick_node(_Node.combine_results)

        # Edges
        self._add_independent_snippets_selection_nodes_edges(_Node.combine_results)
        self.add_edge(_Node.combine_results.__name__, END)

    def create_init_state(
        self,
        problem_statement: str,
        files: list[Path],
        structure: dict,
    ) -> _State:
        return _State(
            problem_statement=problem_statement,
            files=files,
            _localized_functions={},
            structure=structure,
            _localized_classes_functions_lines={},
            final_results={},
        )

    def __call__(
        self,
        root_path: Path,
        problem_statement: str,
        files: list[Path],
        structure: dict | None = None,
    ) -> dict[str, list[list[int]]]:
        structure = create_structure(root_path) if structure is None else structure

        initial_state = self.create_init_state(
            problem_statement=problem_statement,
            files=files,
            structure=structure,
        )

        resp: _State = self.compiled.invoke(initial_state)

        return resp["final_results"]


select_related_snippets_graph = SelectRelatedSnippetsGraph()


if __name__ == "__main__":
    print(f"Saved to: {select_related_snippets_graph.visualize()}")
