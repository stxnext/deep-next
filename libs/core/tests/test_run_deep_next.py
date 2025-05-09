from pathlib import Path

import pytest
from deep_next.common.utils.fs import tmp_git_dir
from deep_next.core.graph import deep_next_graph
from tests.utils import EXAMPLE_REPO_ROOT_DIR, clean

_issue_title = "Add type hints to `src/hello_world.py`"
_issue_description = "Add missing type annotations in `src/hello_world.py`"
_issue_comments = [
    "Should we add the function arguments to the type hints?",
    "Yes, sure.",
    "And should we also add the return types to the type hints?",
    "Yup.",
]

_expected = '''\
diff --git a/src/hello_world.py b/src/hello_world.py
index 534b8eb..9e8a211 100644
--- a/src/hello_world.py
+++ b/src/hello_world.py
@@ -1,4 +1,4 @@
-def say_hello():
+def say_hello() -> None:
     """Say hello!"""
     print("Hello World")

@@ -13,6 +13,6 @@ def foo() -> str:
     return "bar"


-def add_integers(a, b):
+def add_integers(a: int, b: int) -> int:
     """Add two integers."""
     return int(a + b)
'''


@pytest.mark.llm
@pytest.mark.parametrize(
    "root_dir, issue_title, issue_description, issue_comments, expected",
    (
        (
            EXAMPLE_REPO_ROOT_DIR,
            _issue_title,
            _issue_description,
            _issue_comments,
            _expected,
        ),
    ),
)
def test_run_deep_next(
    root_dir: Path,
    issue_title: str,
    issue_description: str,
    issue_comments: str,
    expected: str,
) -> None:
    with tmp_git_dir(root_dir) as git_root_dir:
        git_diff: str = deep_next_graph(
            issue_title=issue_title,
            issue_description=issue_description,
            issue_comments=issue_comments,
            root=git_root_dir,
        )
        assert clean(git_diff) == clean(expected)
