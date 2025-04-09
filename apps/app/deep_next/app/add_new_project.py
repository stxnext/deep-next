from pathlib import Path

from deep_next.app.common import is_snake_case
from deep_next.app.config import (
    AWS_SM_ACCESS_TOKEN_NAME_TMPL,
    CONFIG_FILE_NAME_TMPL,
    CONFIGS_DIR,
)
from deep_next.connectors.aws import AWSSecretsManager
from deep_next.core.io import read_json, write_json
from loguru import logger
from pydantic import BaseModel


class GitLabConfig(BaseModel):
    project_id: int
    base_url: str
    access_token: str


class GitConfig(BaseModel):
    ref_branch: str
    repo_url: str
    label: str


class GitLabProjectConfig(BaseModel):
    """Project configuration for GitLab."""

    _vcs: str = "gitlab"

    project_name: str
    gitlab: GitLabConfig
    git: GitConfig

    def vcs(self) -> str:
        """Version control system."""
        return self._vcs

    def save(self) -> Path:
        """Save configuration to file."""
        file_path = CONFIGS_DIR / CONFIG_FILE_NAME_TMPL.format(
            project_name=self.project_name
        )
        write_json(self.model_dump(), file_path)

        logger.success(f"Saved config for '{self.project_name}': {file_path}")

        return file_path

    @classmethod
    def load(cls, path: Path) -> "GitLabProjectConfig":
        """Load configuration from file."""
        data = read_json(path)

        project_name = data["project_name"]
        logger.debug(f"Loaded config for '{project_name}': '{path}'")

        return cls(**data)


def create_gitlab_project_config(
    project_name: str,
    gitlab_project_id: int,
    git_repo_url: str,
    gitlab_access_token: str,
    gitlab_base_url: str = "https://gitlab.com",
    todo_label: str = "deep_next",
    ref_branch: str = "develop",
) -> GitLabProjectConfig:
    """Create GitLab project configuration."""
    if not is_snake_case(project_name):  # TODO: Pydantic validation
        raise ValueError(f"Project name must be snake case: {project_name}")

    if not git_repo_url.startswith("git@"):  # TODO: Pydantic validation
        raise ValueError(f"Only SSH URLs are supported: {git_repo_url}")

    for config_file in CONFIGS_DIR.iterdir():
        if config_file.name == CONFIG_FILE_NAME_TMPL.format(project_name=project_name):
            raise ValueError(f"Config for '{project_name}' already exists")

    encrypted_token = AWSSecretsManager().create_secret(
        secret_name=AWS_SM_ACCESS_TOKEN_NAME_TMPL.format(project_name=project_name),
        secret_value=gitlab_access_token,
    )

    return GitLabProjectConfig(
        project_name=project_name,
        gitlab=GitLabConfig(
            project_id=gitlab_project_id,
            base_url=gitlab_base_url,
            access_token=encrypted_token,
        ),
        git=GitConfig(
            ref_branch=ref_branch,
            repo_url=git_repo_url,
            label=todo_label,
        ),
    )


if __name__ == "__main__":
    import os

    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    config = create_gitlab_project_config(
        project_name="deep_next",
        gitlab_project_id=462,
        git_repo_url="git@git.stxnext.pl:patryk.laskowski/deep-next.git",
        gitlab_access_token=os.environ["GITLAB_ACCESS_TOKEN"],
        gitlab_base_url="https://git.stxnext.pl",
    )
    path = config.save()

    config2 = GitLabProjectConfig.load(path)
