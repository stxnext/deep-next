from pathlib import Path

from loguru import logger


def _resolve_path(path: Path, abs_dir_path: Path) -> Path | None:
    """Tries to resolve filepath with respect to given directory.

    Note: This is helper tool to depend less on LLM mixed precision.

    Examples:
        > resolve_path("src/foo/bar.py", "/home/user/project/src")
        If file exists, returns "/home/user/project/src/foo/bar.py"

        > resolve_path("project/src/foo/bar.py", "/home/user/project/src")
        If file exists, returns "/home/user/project/src/foo/bar.py"

        > resolve_path("src/foo", "/home/user/project/src")
        If dir exists, returns "/home/user/project/src/foo"
    """
    naive_guess = (abs_dir_path / path).resolve()
    if naive_guess.exists():
        return naive_guess

    parts = Path(path).parts
    for i in range(len(parts)):
        sub_path = abs_dir_path / Path(*parts[i:])
        if sub_path.exists():
            return sub_path.resolve()

    return None


def try_to_resolve_path(path: Path, abs_dir_path: Path) -> Path:
    """If it's a mistake or is it a new file? Try to resolve the path.

    Raises:
        FileNotFoundError: If the path is invalid and cannot be resolved
    """
    resolved = _resolve_path(Path(path), abs_dir_path)

    if resolved:
        return resolved

    logger.info(f"File {path} could not be resolved. Checking if it a new file.")

    file_name = Path(path).name
    parent_dir = Path(path).parent

    if resolved := _resolve_path(parent_dir, abs_dir_path):
        logger.info(f"It's a new file. Resolved to '{str(resolved)}'")
        return resolved / file_name

    raise FileNotFoundError(
        f"Invalid path. Failed to resolve '{str(path)}' with respect to "
        f"'{str(abs_dir_path)}' automatically"
    )
