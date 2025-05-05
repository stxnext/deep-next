from enum import Enum


def label_to_str(label: str | Enum) -> str:
    """Convert label to string."""
    if isinstance(label, Enum):
        return label.value
    return label