from pathlib import Path

import pytest
from deep_next.core.steps.action_plan.srf.graph import select_related_files_graph
from tests.utils import EXAMPLE_REPO_ROOT_DIR, EXAMPLE_REPO_SRC_PATH


@pytest.mark.llm
@pytest.mark.parametrize(
    "query, root_path, expected_files",
    (
        (
            "What file contains `say_hello` function?",
            EXAMPLE_REPO_ROOT_DIR,
            [EXAMPLE_REPO_SRC_PATH / "hello_world.py"],
        ),
    ),
)
def test_find_files_graph(
    query: str,
    root_path: Path,
    expected_files: list[Path],
) -> None:
    files, _, _ = select_related_files_graph(
        root_path=root_path,
        query=query,
    )

    assert all(
        path in files for path in expected_files
    ), f"expected files: {expected_files}\nfound files: {files}"
