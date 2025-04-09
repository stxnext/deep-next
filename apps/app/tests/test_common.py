import pytest
from deep_next.app.common import is_snake_case


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("valid_snake_case", True),
        ("snake_case_with_numbers_123", True),
        ("invalid-SnakeCase", False),
        ("", False),
    ],
)
def test_assert_snake_case(test_input, expected):
    assert is_snake_case(test_input) == expected
