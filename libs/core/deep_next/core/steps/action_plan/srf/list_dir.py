import os
from pathlib import Path


def ls_dir(path: Path) -> str:
    """
    Generate a formatted list of items in a directory.

    This function takes a directory path and lists its contents, including both files
    and subdirectories. Each item is represented in a formatted string, with files
    prefixed by "📄" and directories prefixed by "📁".

    Args:
        path (Path): The path to the directory to list. This should be a valid directory
         path.

    Returns:
        str: A formatted string containing the names of files and directories within the
         specified directory, each on a new line. Directories are indicated with a
         trailing slash.

    Example:
        >>> ls_dir(Path('/path/to/directory'))
        "- 📁 `subdir/`\n- 📄 `file.txt`\n- 📄 `another_file.txt`"
    """
    output = []

    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path):
            output.append(f"- 📁 `{item}/`")
        elif os.path.isfile(full_path):
            output.append(f"- 📄 `{item}`")

    return "\n".join(output)
