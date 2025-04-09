from deep_next.common.config import MONOREPO_ROOT_PATH


def test_monorepo_root_path() -> None:
    assert (MONOREPO_ROOT_PATH / "pyproject.toml").is_file()
    assert (MONOREPO_ROOT_PATH / "apps").is_dir()
    assert (MONOREPO_ROOT_PATH / "libs").is_dir()
