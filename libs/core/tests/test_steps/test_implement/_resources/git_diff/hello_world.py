def say_hello():
    """Say hello!"""
    print("Hello World")


def log(msg: str) -> None:
    """Logging function."""
    print(f">>> {msg}")


def foo() -> str:
    return "bar"


def add_integers(a, b):
    """Add two integers."""
    return int(a + b)
