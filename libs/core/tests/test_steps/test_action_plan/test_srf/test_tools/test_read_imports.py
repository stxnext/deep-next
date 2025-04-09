from deep_next.core import config
from deep_next.core.steps.action_plan.srf.file_selection.tools.read_imports import (
    _read_imports,
)

RESOURCES = config.ROOT_DIR / "tests" / "_resources"
EXAMPLE_MODULE_PATH = RESOURCES / "example_project"


def test_read_imports():
    example_file = "src/model.py"
    imports = _read_imports(EXAMPLE_MODULE_PATH, example_file)

    expected = "Imports for src/model.py:\n" "    └── import: pydantic\n"

    assert imports == expected
