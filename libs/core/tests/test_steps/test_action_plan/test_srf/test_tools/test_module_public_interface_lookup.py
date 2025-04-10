from deep_next.core import config
from deep_next.core.steps.action_plan.srf.file_selection.tools.module_public_interface_lookup import (  # noqa: E501
    _interface_tree,
)

RESOURCES = config.ROOT_DIR / "tests" / "_resources"
EXAMPLE_MODULE_PATH = RESOURCES / "example_project"


def test_module_public_interface_lookup():
    example_file = "src/model.py"

    actual = _interface_tree(EXAMPLE_MODULE_PATH / example_file)
    expected = (
        "└── module: model\n"
        "    └── class HelloWorldResponse\n"
        "        ├── def greet(self: Any) -> None"
    )

    assert actual == expected
