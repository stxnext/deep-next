from pathlib import Path
from typing import Annotated

from deep_next.core.steps.gather_project_knowledge.project_map import tree
from langchain_core.tools import tool


def list_file_structure_tool_builder(root_path: Path):
    @tool
    def list_file_structure(
        directory: Annotated[str, "The root directory to generate the tree for."]
    ) -> Annotated[
        str,
        (
            "A string representation of the directory tree, formatted using the `rich` "
            "library for visual clarity."
        ),
    ]:
        """
        Generates a visual directory tree structure for a given path.

        Generates a visual directory tree structure for a given path. If a tree node
        consists of more than {N_BIG_BRANCH_ITEMS} items, it is cut off and marked with
        "📁 <found X items>".

        Example output:
        ```text
        📁 src
        ├── 📁 module1
        │   ├── 📄 __init__.py
        │   ├── 📄 file1.py
        │   └── 📄 file2.py
        ├── 📁 module2
        │   └── 📄 file3.py
        │   📄 main.py
        📁 docs
        ├── 📄 index.md
        📄 README.md
        ```
        """
        return tree(root_path / directory, directory)

    return list_file_structure
