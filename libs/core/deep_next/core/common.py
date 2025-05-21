import textwrap
import traceback
from pathlib import Path

from deep_next.core.io import read_txt


# TODO: Remove. It's moved to common lib.
def gitignore_name(name: str) -> str:
    """Converts the name so that it'll be ignored by git."""
    return f"___{name}"


def dump_filepaths(file_paths: list[Path | str]) -> str:
    """Create a dump of the contents of the given file paths."""
    file_repr_tmpl = textwrap.dedent(
        """
        Path: {abs_path}
        ```python
        {code}
        ```
        """
    )
    file_paths = [str(Path(path).resolve()) for path in file_paths]

    dump = [
        file_repr_tmpl.format(abs_path=file_path, code=read_txt(file_path))
        for file_path in file_paths
    ]

    return "\n".join(dump)


def format_exception(e: Exception) -> str:
    return ''.join(
        traceback.format_exception(type(e), value=e, tb=e.__traceback__)
    )