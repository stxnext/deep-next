import pytest
from deep_next.core.steps.implement.acr import lint_python_content


@pytest.mark.parametrize(
    "code_snippet,expected_result",
    [
        ("def add(a, b):\n    return a + b", True),
        ("def bad()\n    return 1", False),
        ("def wrong_indent():\nprint('oops')", False),
        ("", True),
        ("def BadName():\n    return 123", True),
        ("def error():\n    return 1 / 0", True),
        ('def x():\n    print("oops)', False),
        ("def x():\n    return $123", False),
        (r"def x():\n    s = '\udc80'", False),
    ],
)
def test_lint_python_content(code_snippet, expected_result):
    result = lint_python_content(code_snippet)
    assert result == expected_result
