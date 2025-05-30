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
