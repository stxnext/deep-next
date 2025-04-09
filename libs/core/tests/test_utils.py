from pathlib import Path

import pytest
from deep_next.common.utils.fs import tmp_git_dir
from tests.utils import EXAMPLE_REPO_ROOT_DIR


def _is_git_repo(dir_path: Path) -> bool:
    return (dir_path / ".git").is_dir()


@pytest.mark.parametrize("repo_dir", (EXAMPLE_REPO_ROOT_DIR,))
def test_tmp_git_dir(repo_dir: Path) -> None:

    with tmp_git_dir(repo_dir) as git_root_dir:

        assert repo_dir.exists()
        assert not _is_git_repo(repo_dir)
        assert git_root_dir.exists()
        assert _is_git_repo(git_root_dir)

    assert repo_dir.exists()
    assert not _is_git_repo(repo_dir)
    assert not git_root_dir.exists()
