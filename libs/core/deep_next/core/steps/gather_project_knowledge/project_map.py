import os
import re
from io import StringIO
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

N_BIG_BRANCH_ITEMS = 50


def _is_valid_dir(path: Path) -> bool:
    return (
        not path.name.startswith("test_")
        and path.name != "tests"
        and not path.name.startswith("__")
        and not path.name.startswith(".")
    )


def _is_valid_file(path: Path) -> bool:
    return (
        path.name.endswith(".py")
        and not re.match(r"^_[^_]", path.name)
        and not path.name.startswith("test_")
    )


def _build_tree(directory: Path, tree: Tree) -> None:
    for path in sorted(directory.iterdir()):
        if path.is_dir() and _is_valid_dir(path):
            branch = tree.add(f"📁 {path.name}")
            if len(os.listdir(path)) > N_BIG_BRANCH_ITEMS:
                branch.add(f"📁 <found {len(os.listdir(path))} items>")
            else:
                _build_tree(path, branch)
        elif path.is_file() and _is_valid_file(path):
            tree.add(f"📄 {path.name}")


def tree(path: Path | str, root_name: str | None = None) -> str:
    """
    Generates a visual directory tree structure for a given path.

    Generates a visual directory tree structure for a given path. If a tree node
    consists of more than {N_BIG_BRANCH_ITEMS} items, it is cut off and marked with:
    "📁 <found X items>".

    Args:
        path (Path | str): The root directory to generate the tree for.
        root_name (str | None): The name of the root node of the tree.

    Returns:
        str: A string representation of the directory tree, formatted using
             the `rich` library for visual clarity.

    Example:
        >>> from pathlib import Path
        >>> print(tree(Path("src")))
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
    """
    path = Path(path)
    project_tree = Tree(f"📁 {root_name}" or "")

    _build_tree(path, project_tree)

    output = StringIO()
    console = Console(file=output, force_jupyter=False, force_terminal=True)

    console.print(project_tree)

    result = output.getvalue()

    if root_name:
        return result

    # Remove the first line, as it's the root node: "📁 None\n"
    result = result[result.index("\n") + 1 :]  # noqa: E203

    # from each line remove the first 4 characters, as the root node is not needed
    flat_tree = "\n".join([line[4:] for line in result.split("\n")])

    return flat_tree
