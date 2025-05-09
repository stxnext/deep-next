from enum import Enum


def label_to_str(label: str | Enum | None) -> str | None:
    """Convert label to string."""
    if label is None:
        return None

    if isinstance(label, Enum):
        return label.value
    return label
