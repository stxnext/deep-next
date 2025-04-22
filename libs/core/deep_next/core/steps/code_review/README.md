# Code Review (CR) Module

## Overview

The CR (Code Review) module is responsible for evaluating if the code change produced by DeepNext fulfills all requirements. The requirements can be defined in separate code reviewers, each of which has a given responsibility in terms of evaluating the code.

## Key Components

### Core Classes

- `Code Style Code Reviewer`: Look for missing or incorrect docstrings, type hints in places where they are needed, naming of variables, functions, classes, code-formatting e.g.: missing or extra spaces, parenthesis, etc.
- `Diff Consistency Code Reviewer`: Situations, when a newly created or already existing utility, function, class or other piece of code is used with a mistake, incorrect arguments, in the wrong context, or when it could be used, but is repeated.

## Workflow

1. The process starts with an **root path**, **issue description**, **project description** and **git diff**
2. If `include_code_fragments` is `True`, the graph selects relevant snippets from the codebase based on the issue description, project description and git diff
3. All input and gathered information are sequentially passed to the code reviewers, which return a list of issues

## Example Usage

```python
from deep_next.core.steps.code_review import code_review_graph

issue_statement = ("Missing type annotations in `src/hello_world.py`. Add missing "
                   "type annotations in `src/hello_world.py`")

git_diff = '''\
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
+def add_integers(a: int, b: int):
     """Add two integers."""
     return int(a + b)
'''

result = code_review_graph(
    root_path=Path("not/important/if/not/include_code_fragments"),
    issue_statement=issue_statement,
    project_knowledge="",
    git_diff=git_diff,
    include_code_fragments=False,
)

print(result.issues)
# [
#     (
#          'code_style_code_reviewer',
#          "The function 'add_integers' in the file 'src/hello_world.py' does not "
#          "have a type hint for its return value. It should have a type hint "
#          "indicating that it returns an int."
#     )
# ]
```

## Architecture Notes

- Built on LangGraph for workflow orchestration
- Utilizes LLMs to review the code
- Modular design allows for easy addition of new reviewers
