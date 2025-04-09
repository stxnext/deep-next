import re


def is_snake_case(txt: str) -> bool:
    """Makes sure that the given string is in snake_case."""
    snake_case_pattern = r"^[a-z0-9]+(_[a-z0-9]+)*$"
    return bool(re.match(snake_case_pattern, txt))
