import os
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class EnvVars:
    VCS = "VCS_PROVIDER"
    ACCESS_TOKEN = "VCS_ACCESS_TOKEN"
    REPO_PATH = "VCS_REPO_PATH"
    BASE_URL = "VCS_BASE_URL"


class VCSConfig(BaseModel, ABC):
    vcs: Literal["github", "gitlab"] = Field(description="Version control system")
    access_token: str = Field(description="Access token for the VCS")
    repo_path: str = Field(description="Repository path (user/repo or group/project)")
    base_url: str | None = Field(default=None, description="Base URL for the VCS")

    @property
    @abstractmethod
    def clone_url(self) -> str:
        """Abstract property for clone URL."""


class GitHubConfig(VCSConfig):
    vcs: Literal["github"] = "github"

    @property
    def clone_url(self) -> str:
        return f"https://{self.access_token}@github.com/{self.repo_path}.git"


class GitLabConfig(VCSConfig):
    vcs: Literal["gitlab"] = "gitlab"
    base_url: str = Field(default="gitlab.com", description="GitLab instance base URL")

    @property
    def clone_url(self) -> str:
        return (
            "https://gitlab-ci-token:"
            f"{self.access_token}@{self.base_url}/{self.repo_path}.git"
        )


def load_vcs_config_from_env() -> VCSConfig:
    try:
        vcs = os.getenv("VCS", "github")

        common_data = {
            "access_token": os.environ[EnvVars.ACCESS_TOKEN],
            "repo_path": os.environ[EnvVars.REPO_PATH],
        }

        if vcs == "gitlab":
            return GitLabConfig(
                **common_data, base_url=os.getenv(EnvVars.BASE_URL, "gitlab.com")
            )
        elif vcs == "github":
            return GitHubConfig(**common_data)
        else:
            raise ValueError(f"Unsupported VCS type: '{vcs}'")

    except KeyError as e:
        raise KeyError(f"Missing environment variable: '{e}'")
