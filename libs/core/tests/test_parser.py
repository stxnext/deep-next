import pytest
from deep_next.core.parser import extract_from_tag_block, has_tag_block, parse_tag_block


@pytest.mark.parametrize(
    "txt, code_type, expected",
    [
        (
            "<python>\nprint('Hello, World!')\n</python>",
            "python",
            "print('Hello, World!')",
        ),
        ("Some text without code block", "python", ""),
        ("<python>\nx = 42\n</python>", "python", "x = 42"),
        ("<python>x = 42</python>", "python", ""),
    ],
)
def test_extract_code_from_block(txt: str, code_type: str, expected: str) -> None:
    assert extract_from_tag_block(txt, code_type) == expected


@pytest.mark.parametrize(
    "txt, code_type, expected",
    [
        ("<python>\nprint('Hello, World!')\n</python>", "python", True),
        ("Some text without code block", "python", False),
        ("<python>\nx = 42\n</python>", "javascript", False),
    ],
)
def test_has_code_block(txt: str, code_type: str, expected: bool) -> None:
    assert has_tag_block(txt, code_type) == expected


@pytest.mark.parametrize(
    "txt, code_type, expected",
    [
        (
            "<python>\nprint('Hello, World!')\n</python>",
            "python",
            "<python>\nprint('Hello, World!')\n</python>",
        ),
    ],
)
def test_parse_code_block(txt: str, code_type: str, expected: str):
    assert parse_tag_block(txt, code_type) == expected
