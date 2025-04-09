from pathlib import Path

from deep_next.core.steps.action_plan.srf.file_selection.tools.list_file_structure import (  # noqa: E501
    list_file_structure_tool_builder,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.module_public_interface_lookup import (  # noqa: E501
    module_public_interface_lookup_tool_builder,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.read_file import (
    read_file_tool_builder,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.read_imports import (
    read_imports_tool_builder,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.search import (
    dispose_acr_backend,
    init_acr_backend,
    search_class_in_file_tool_builder,
    search_class_tool_builder,
    search_code_in_file_tool_builder,
    search_code_tool_builder,
    search_method_in_class_tool_builder,
    search_method_in_file_tool_builder,
    search_method_tool_builder,
)
from langgraph.prebuilt import ToolNode

_llm_tools: dict[Path, list] = {}
_tool_nodes: dict[Path, ToolNode] = {}


def init_tools(root_path: Path):
    init_acr_backend(root_path)
    llm_tools = build_llm_tools(root_path)
    _llm_tools[root_path] = llm_tools
    _tool_nodes[root_path] = ToolNode(llm_tools, messages_key="_messages")


def get_llm_tools(root_path: Path):
    return _llm_tools[root_path]


def get_tool_node(root_path: Path):
    return _tool_nodes[root_path]


def dispose_tools(root_path: Path):
    dispose_acr_backend(root_path)
    del _llm_tools[root_path]
    del _tool_nodes[root_path]


def build_llm_tools(root_path: Path) -> list:
    """Build the tools for the given source path."""
    return [
        # Simple search tools
        search_class_tool_builder(root_path),
        search_method_tool_builder(root_path),
        search_code_tool_builder(root_path),
        # Advanced search tools
        search_class_in_file_tool_builder(root_path),
        search_method_in_file_tool_builder(root_path),
        search_method_in_class_tool_builder(root_path),
        search_code_in_file_tool_builder(root_path),
        # Lookup tools
        list_file_structure_tool_builder(root_path),
        read_file_tool_builder(root_path),
        read_imports_tool_builder(root_path),
        module_public_interface_lookup_tool_builder(root_path),
    ]
