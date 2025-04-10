from pathlib import Path

import pytest
from deep_next.core.steps.action_plan.path_tools import _resolve_path
from tests.utils import EXAMPLE_REPO_ROOT_DIR, EXAMPLE_REPO_SRC_PATH


@pytest.mark.parametrize(
    "filepath, dir_path, expected",
    [
        (
            "hello_world.py",
            EXAMPLE_REPO_SRC_PATH,
            EXAMPLE_REPO_SRC_PATH / "hello_world.py",
        ),
        (
            "src/hello_world.py",
            EXAMPLE_REPO_SRC_PATH,
            EXAMPLE_REPO_SRC_PATH / "hello_world.py",
        ),
        (
            "_resources/example_project/src/hello_world.py",
            EXAMPLE_REPO_SRC_PATH,
            EXAMPLE_REPO_SRC_PATH / "hello_world.py",
        ),
        (
            "_resources/example_project/src",
            EXAMPLE_REPO_ROOT_DIR,
            EXAMPLE_REPO_SRC_PATH,
        ),
        ("_resources/example_project/src/missing/path", EXAMPLE_REPO_SRC_PATH, None),
    ],
)
def test_resolve_path(filepath: str, dir_path: Path, expected):
    assert _resolve_path(Path(filepath), dir_path) == expected
