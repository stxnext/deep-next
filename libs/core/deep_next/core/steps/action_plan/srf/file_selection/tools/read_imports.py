import ast
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


def _find_module_file(root_path: Path, import_path: str) -> Path | None:
    """
    Find the absolute path of a module within the src_path repository.

    Args:
        root_path (Path): The root path of the repository.
        import_path (str): The dot-separated import path (e.g.,
        'package.subpackage.module').

    Returns:
        Optional[pathlib.Path]: The absolute path to the module file if found
        within src_path, else None.
    """
    # Split the import path into parts
    parts = import_path.split(".")
    current_path = root_path.parent

    for i, part in enumerate(parts):
        # Candidate paths for the current module part
        module_file = current_path / f"{part}.py"
        module_init = current_path / part / "__init__.py"

        if module_file.is_file():
            if i == len(parts) - 1:
                return module_file.resolve()
            else:
                # It's a module file but there are more parts; invalid path
                return None
        elif module_init.is_file():
            current_path = current_path / part
        else:
            # Module not found in src_path
            return None

    # If the loop completes without returning, it means the last part was a package
    # So return its __init__.py
    init_file = current_path / "__init__.py"
    if init_file.is_file():
        return init_file.resolve()

    return None


def _read_imports(
    root_path: Path,
    file_path: Annotated[str, "Path to the file whose imports to read."],
) -> Annotated[str, "Tree-like representation of the imports of a Python file."]:
    """
    Look up the imports of a given *.py module.

    Example output:

    ```text
    Imports for config.py:
        └── import: os
        └── import: sys
        └── import: typing
        └── import: foo (filepath: src/foo.py)
    ```
    """
    abs_path = root_path / Path(file_path)

    if not abs_path.exists():
        return f"File `{file_path}` not found."

    with open(abs_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path)

    imports = []
    for item in ast.walk(node):
        if isinstance(item, ast.Import):
            for alias in item.names:
                imports.append(alias.name)
        elif isinstance(item, ast.ImportFrom):
            imports.append(item.module)

    result = f"Imports for {file_path}:\n"
    for imp in imports:
        try:
            path = _find_module_file(imp)
            module_file = root_path / Path(path).relative_to(root_path)
        except Exception:
            module_file = None

        result += f"    └── import: {imp}"
        if module_file:
            result += f" (filepath: {module_file})"
        result += "\n"

    return result


def read_imports_tool_builder(root_path: Path):
    @tool
    def read_imports_tool(
        file_path: Annotated[str, "Path to the file whose imports to read."]
    ) -> Annotated[str, "Tree-like representation of the imports of a Python file."]:
        """
        Look up the imports of a given *.py module.

        Example output:

        ```text
        Imports for config.py:
            └── import: os
            └── import: sys
            └── import: typing
            └── import: foo (filepath: src/foo.py)
        ```
        """
        return _read_imports(root_path, file_path)

    return read_imports_tool
