from pathlib import Path

import pytest
from deep_next.core.steps.gather_project_knowledge.project_description import (
    create_project_description,
)
from tests.utils import EXAMPLE_REPO_ROOT_DIR


@pytest.mark.llm
@pytest.mark.parametrize("root_dir", (EXAMPLE_REPO_ROOT_DIR,))
def test_create_project_description(root_dir: Path) -> None:
    project_description = create_project_description(root_dir)

    expected_labels = [
        "Purpose / Primary Goals",
        "Project Structure",
        "Entry Points",
        "Important Classes / Modules",
        "Tech Stack Overview",
        "Architecture Overview",
    ]

    assert isinstance(project_description, str)
    assert all(
        label.lower() in project_description.lower() for label in expected_labels
    )
