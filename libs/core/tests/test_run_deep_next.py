from pathlib import Path

import pytest
from deep_next.common.utils.fs import tmp_git_dir
from deep_next.core.graph import deep_next_graph
from tests.utils import EXAMPLE_REPO_ROOT_DIR, clean

_problem_statement = (
    "Missing type annotations in `src/hello_world.py`. Add missing type annotations in "
    "`src/hello_world.py`"
)
_hints = "\n".join(
    [
        "Should we add the function arguments to the type hints?",
        "Yes, sure.",
        "And should we also add the return types to the type hints?",
        "Yup.",
    ]
)
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
    "root_dir, problem_statement, hints, expected",
    ((EXAMPLE_REPO_ROOT_DIR, _problem_statement, _hints, _expected),),
)
def test_run_deep_next(
    root_dir: Path, problem_statement: str, hints: str, expected: str
) -> None:
    with tmp_git_dir(root_dir) as git_root_dir:
        git_diff: str = deep_next_graph(
            problem_statement=problem_statement,
            hints="\n".join(hints),
            root=git_root_dir,
        )
        assert clean(git_diff) == clean(expected)
