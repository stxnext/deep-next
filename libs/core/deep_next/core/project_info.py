import functools
import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from deep_next.core.io import read_txt
from loguru import logger

NOT_FOUND = "<NOT FOUND>"


def find_readme(root_path: Path) -> Path | None:
    for p in root_path.iterdir():
        if p.name.startswith("README"):
            return p


def find_pyproject_toml(root_path: Path) -> Path | None:
    path = root_path / "pyproject.toml"
    return path if path.exists() else None


def find_setup_py(root_path: Path) -> Path | None:
    path = root_path / "setup.py"
    return path if path.exists() else None


def find_setup_cfg(root_path: Path) -> Path | None:
    path = root_path / "setup.cfg"
    return path if path.exists() else None


def _log_if_different_than_dir(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        resp = func(self, *args, **kwargs)

        if resp != self.root_dir.name:
            logger.warning(
                f"Returned project name `{resp}` is different than "
                f"its root dir name `{self.root_dir.name}`"
            )

        return resp

    return wrapper


@dataclass(frozen=True)
class ProjectInfo:
    root_dir: Path

    pyproject_toml: str = NOT_FOUND
    setup_py: str = NOT_FOUND
    setup_cfg: str = NOT_FOUND
    readme: str = NOT_FOUND

    def _get_name_from_pyproject_toml_tool(self) -> str | None:
        pyproject_dict: dict[str, Any] = tomllib.loads(self.pyproject_toml)
        try:
            return pyproject_dict["tool"]["poetry"]["name"].lower()
        except KeyError:
            return None

    def _get_name_from_pyproject_toml_project(self) -> str | None:
        pyproject_dict: dict[str, Any] = tomllib.loads(self.pyproject_toml)
        try:
            return pyproject_dict["project"]["name"].lower()
        except KeyError:
            return None

    @property
    @_log_if_different_than_dir
    def name(self) -> str:
        if self.pyproject_toml != NOT_FOUND:
            if result := self._get_name_from_pyproject_toml_tool():
                return result

            if result := self._get_name_from_pyproject_toml_project():
                return result

        if self.setup_py != NOT_FOUND:
            pattern = r"name ?= ?(\"|'| )?(?P<name>[\w\-_]+)(\"|'| )?"
            match = re.search(pattern, self.setup_py)
            if match:
                return match.group("name").lower()

        if self.setup_cfg != NOT_FOUND:
            pattern = r"name ?= ?(\"|'| )?(?P<name>[\w\-_]+)(\"|'| )?"
            match = re.search(pattern, self.setup_cfg)
            if match:
                return match.group("name").lower()

        raise Exception("Project name not found. This is critical problem.")


@lru_cache(maxsize=1)
def get_project_info(root_dir: Path) -> ProjectInfo:
    paths = {
        "pyproject_toml": find_pyproject_toml(root_dir),
        "setup_py": find_setup_py(root_dir),
        "setup_cfg": find_setup_cfg(root_dir),
        "readme": find_readme(root_dir),
    }
    data = {name: read_txt(path) for name, path in paths.items() if path}

    return ProjectInfo(
        root_dir=root_dir,
        **data,
    )
