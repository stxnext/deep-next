import os
from pathlib import Path
from typing import TYPE_CHECKING

from deep_next.connectors.version_control_provider import (
    BaseConnector,
    GitHubConnector,
    GitLabConnector,
)

if TYPE_CHECKING:
    from deep_next.app.vcs_config import VCSConfig


def convert_paths_to_str(json_obj):
    """Recursively convert Path objects to strings in nested dictionaries and lists."""
    if isinstance(json_obj, dict):
        return {k: convert_paths_to_str(v) for k, v in json_obj.items()}
    elif isinstance(json_obj, list):
        return [convert_paths_to_str(item) for item in json_obj]
    elif isinstance(json_obj, Path):
        return f"Path({str(json_obj)})"
    else:
        return json_obj


def convert_str_to_paths(json_obj):
    """
    Convert paths into strings.

    Recursively convert strings representing Path objects back to Path objects in nested
    dictionaries and lists.
    """
    if isinstance(json_obj, dict):
        return {k: convert_str_to_paths(v) for k, v in json_obj.items()}
    elif isinstance(json_obj, list):
        return [convert_str_to_paths(item) for item in json_obj]
    elif (
        isinstance(json_obj, str)
        and json_obj.startswith("Path(")
        and json_obj.endswith(")")
    ):
        path_str = json_obj[5:-1]  # Remove "Path(" at the beginning and ")" at the end
        return Path(path_str)
    else:
        return json_obj


def get_connector(config: "VCSConfig") -> BaseConnector:
    """Creates a connector for the given project configuration."""
    if config.vcs == "github":
        return GitHubConnector(
            token=config.access_token,
            repo_name=config.repo_path,  # TODO: Fix naming
        )
    elif config.vcs == "gitlab":
        return GitLabConnector(
            access_token=config.access_token,
            repo_name=config.repo_path,
            base_url=config.base_url,
        )
    else:
        raise ValueError(
            f"Unsupported VCS, can't find related connector: '{config.vcs}'"
        )



