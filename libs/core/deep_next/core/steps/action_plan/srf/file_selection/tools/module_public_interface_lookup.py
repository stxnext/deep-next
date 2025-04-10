import ast
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


def _is_public(name: str) -> bool:
    """Check if a name is considered public (does not start with an underscore)."""
    return not name.startswith("_")


def _infer_type(node: ast.AST) -> str:
    """Infer type from AST node."""
    if node is None:
        return "Any"
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Subscript):
        base_type = _infer_type(node.value)
        if isinstance(node.slice, ast.Index):
            item_type = _infer_type(node.slice.value)
        elif isinstance(node.slice, ast.Tuple):
            item_types = [_infer_type(item) for item in node.slice.elts]
            item_type = f"[{', '.join(item_types)}]"
        else:
            item_type = _infer_type(node.slice)
        return f"{base_type}[{item_type}]"
    elif isinstance(node, ast.Attribute):
        return f"{_infer_type(node.value)}.{node.attr}"
    elif isinstance(node, ast.Str):
        return "str"
    elif isinstance(node, ast.Num):
        return type(node.n).__name__
    return "Any"


def _parse_python_file(file_path: Path, prefix="") -> str:
    """Parse a Python file and return its public interface."""
    resp = []

    with file_path.open("r", encoding="utf-8") as file:
        node = ast.parse(file.read(), filename=str(file_path))

    module_name = file_path.stem
    resp.append(f"{prefix}└── module: {module_name}")

    new_prefix = prefix + "    "
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name) and _is_public(target.id):
                    resp.append(
                        f"{new_prefix}├── {target.id}: {_infer_type(child.value)}"
                    )
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(child.name):
                args = ", ".join(
                    f"{arg.arg}: {_infer_type(arg.annotation)}"
                    for arg in child.args.args
                )
                return_type = _infer_type(child.returns) if child.returns else "None"
                resp.append(
                    f"{new_prefix}├── def {child.name}({args}) -> {return_type}"
                )
                docstring = ast.get_docstring(child)
                if docstring:
                    resp.extend(
                        [f"{new_prefix}│   > {line}" for line in docstring.split("\n")]
                    )
        elif isinstance(child, ast.ClassDef) and _is_public(child.name):
            resp.append(f"{new_prefix}└── class {child.name}")
            class_prefix = new_prefix + "    "
            for field in child.body:
                if isinstance(field, ast.AnnAssign) and _is_public(field.target.id):
                    field_type = _infer_type(field.annotation)
                    resp.append(f"{class_prefix}├── {field.target.id}: {field_type}")
                elif isinstance(field, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _is_public(field.name):
                        args = ", ".join(
                            f"{arg.arg}: {_infer_type(arg.annotation)}"
                            for arg in field.args.args
                        )
                        return_type = (
                            _infer_type(field.returns) if field.returns else "None"
                        )
                        resp.append(
                            f"{class_prefix}"
                            f"├── def {field.name}({args}) -> {return_type}"
                        )
                        docstring = ast.get_docstring(field)
                        if docstring:
                            resp.extend(
                                [
                                    f"{class_prefix}│   > {line}"
                                    for line in docstring.split("\n")
                                ]
                            )
    return "\n".join(resp)


def _interface_tree(file_path: Path | str) -> str:
    """Generate a tree-like representation of the public interface of a Python file.

    Args:
        file_path (Path): Path to the Python file.

    Returns:
        str: Formatted string representing the file's public interface.
    """
    file_path = Path(file_path)
    if (
        not file_path.exists()
        or not file_path.is_file()
        or not file_path.suffix == ".py"
    ):
        raise ValueError(f"Invalid Python file: {file_path}")
    return _parse_python_file(file_path)


def module_public_interface_lookup_tool_builder(root_path: Path):
    """Build a tool to look up the public interface of a given *.py module."""

    @tool
    def module_public_interface_lookup(
        file_path: Annotated[str, "Path to the file to explore."]
    ) -> Annotated[
        str, "Tree-like representation of the public interface of a Python file."
    ]:
        """
        Look up the public interface of a given *.py module.

        Example output:

        ```text
        Interface for config.py:
            └── module: config
                └── class Config
                    ├── API_KEY: str
                    ├── BASE_URL: str
                    ├── def get_url(self: Any) -> str
                    │   > Return the base URL for the API.
                    │   >
                    │   > Returns:
                    │   >     str: The base URL as a string.
        ```
        """
        return _interface_tree(file_path=root_path / Path(file_path))

    return module_public_interface_lookup
