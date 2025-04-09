from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Awaitable, Callable, Hashable, Union

from deep_next.core.common import gitignore_name
from deep_next.core.config import DATA_DIR
from langchain_core.runnables.base import Runnable, RunnableLike
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from typing_extensions import Self, TypedDict


class State(TypedDict):
    pass


class _WrappedCompiledStateGraph(CompiledStateGraph):
    """Wrapper for CompiledStateGraph to add setup and teardown logic."""

    def __init__(
        self,
        compiled_graph: CompiledStateGraph,
        setup_fn: Callable[[State], None],
        teardown_fn: Callable[[State], None],
    ):
        self._compiled_graph = compiled_graph
        self._setup_fn = setup_fn
        self._teardown_fn = teardown_fn

        self.__dict__.update(self._compiled_graph.__dict__)

    def invoke(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Run setup -> original invoke -> teardown."""
        state = kwargs.get("input", args[0])

        self._setup_fn(state)

        try:
            return self._compiled_graph.invoke(*args, **kwargs)
        finally:
            self._teardown_fn(state)


class BaseGraph(StateGraph, ABC):
    def __init__(
        self,
        state_cls: type[State | BaseModel],
    ):
        super().__init__(state_cls)
        self.setup_fn = lambda _: None
        self.teardown_fn = lambda _: None
        self._build()
        self.compiled = _WrappedCompiledStateGraph(
            self.compile(),
            self.setup_fn,
            self.teardown_fn,
        )

    def set_setup_fn(self, setup_fn: Callable[[State], None]) -> Self:
        self.setup_fn = setup_fn
        return self

    def set_teardown_fn(self, teardown_fn: Callable[[State], None]) -> Self:
        self.teardown_fn = teardown_fn
        return self

    @abstractmethod
    def __call__(self, *args, **kwargs) -> State:
        """Simplified interface to call a graph.

        Note: When using in node, the sub-graph won't be visible in visualization.
            To have a sub-graph visualized properly it is required
            to call a `CompiledGraph` directly:
            > graph = ChildOfBaseGraph()
            > graph.compiled.invoke(...)
        """

    @abstractmethod
    def _build(self) -> None:
        """Override this method to build the graph.

        Example:
            ```
            self.add_node("node_1", node_function_1)
            self.add_node("node_2", node_function_2)
            self.add_node("node_3", node_function_3)

            self.add_edge(START, "node_1")
            self.add_edge("node_1", "node_2")
            self.add_edge("node_2", "node_3")
            self.add_edge("node_3", END)
            ```
        """

    def add_quick_node(self, action: RunnableLike) -> Self:
        return self.add_node(action.__name__, action)

    def add_quick_edge(
        self, from_node: RunnableLike | str, to_node: RunnableLike | str
    ) -> Self:
        return self.add_edge(
            from_node if isinstance(from_node, str) else from_node.__name__,
            to_node if isinstance(to_node, str) else to_node.__name__,
        )

    def add_quick_conditional_edges(
        self,
        source: RunnableLike,
        path: Union[
            Callable[..., Union[Hashable, list[Hashable]]],
            Callable[..., Awaitable[Union[Hashable, list[Hashable]]]],
            Runnable[Any, Union[Hashable, list[Hashable]]],
        ],
    ) -> Self:
        return self.add_conditional_edges(
            source.__name__,
            path,
        )

    @abstractmethod
    def create_init_state(self, *args, **kwargs) -> State:
        """Creates initial state for given graph."""

    def visualize(self, output_file_path: Path | None = None, subgraph_depth=2) -> Path:
        if not output_file_path:
            output_file_path = (
                DATA_DIR
                / "visualize"
                / gitignore_name(f"graph_{self.__class__.__name__}.png")
            )
        self.compiled.get_graph(xray=subgraph_depth).draw_mermaid_png(
            output_file_path=str(output_file_path)
        )
        return output_file_path
