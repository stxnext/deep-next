import json
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any


def read_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def write_txt(txt: str, path: Path) -> Path:
    with open(path, "w") as f:
        f.write(txt)
    return path


def read_txt(path: Path | str) -> str:
    """Reads the contents of a text file and returns it as a string.

    Args:
        path (Path | str): Path to text file.

    Returns:
        str: The contents of the text file.
    """
    path = Path(path)
    with open(path, "r") as f:
        return f.read()


def read_txt_or_none(path: Path | str) -> str | None:
    try:
        return read_txt(path)
    except Exception:
        return None


def write_json(data: Any, path: Path) -> Path:
    """Saves the given data as a JSON file."""
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except TypeError as e:
        raise ValueError(f"Provided data is not serializable to JSON: {data}") from e
    except IOError as e:
        raise IOError(f"Could not write to file: {path}") from e

    return path


def read_json(path: Path) -> Any:
    """Reads a JSON file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"File does not exist: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"File content is not valid JSON: {path}") from e
    except IOError as e:
        raise IOError(f"Could not read from file: {path}") from e


def copy_directory_to_temp(root_dir: Path) -> Path:
    """Copies directory to temporary dir."""
    root_dir = Path(root_dir)
    temp_dir = Path(tempfile.mkdtemp())

    dest_dir = temp_dir / root_dir.name

    shutil.copytree(root_dir, dest_dir)

    return dest_dir
