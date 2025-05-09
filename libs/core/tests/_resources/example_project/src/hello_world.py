def say_hello() -> None:
    """Say hello!"""
    print("Hello World")


def log(msg: str) -> None:
    """Logging function."""
    print(f">>> {msg}")


def foo() -> str:
    """Return the string 'bar'."""
    return "bar"


def add_integers(a: int, b: int) -> int:
    """Add two integers."""
    return int(a + b)
