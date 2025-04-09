import pytest
from deep_next.core import config
from deep_next.core.steps.gather_project_knowledge.project_map import tree

_path = config.ROOT_DIR / "tests" / "_resources" / "example_project"
_expected = """\
📁 src
├── 📄 __init__.py
├── 📄 hello_world.py
└── 📄 model.py
"""

_expected_root_name = """\
📁 example_project
└── 📁 src
    ├── 📄 __init__.py
    ├── 📄 hello_world.py
    └── 📄 model.py
"""


@pytest.mark.parametrize(
    "path, expected, with_root_name",
    (
        (_path, _expected, False),
        (_path, _expected_root_name, True),
    ),
)
def test_tree(path, expected, with_root_name: bool) -> None:
    actual = tree(path, root_name=path.name if with_root_name else None)

    assert actual == expected
