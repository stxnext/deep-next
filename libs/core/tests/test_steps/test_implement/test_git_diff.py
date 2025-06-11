import shutil

from deep_next.common.utils.fs import create_tmp_dir, tmp_git_dir
from deep_next.core import config
from deep_next.core.steps.implement.git_diff import apply_diff, generate_diff
from tests.utils import clean

RESOURCES = config.ROOT_DIR / "tests" / "test_steps" / "test_implement" / "_resources"


def test_git_diff_components() -> None:
    """Tests git diff apply mechanism as well as git diff generator."""
    file_to_change = RESOURCES / "git_diff" / "hello_world.py"
    git_diff_file = RESOURCES / "git_diff" / "hello_world.diff"

    expected_git_diff = git_diff_file.read_text(encoding="utf-8")

    with create_tmp_dir() as tmp_dir:
        src_dir = tmp_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(file_to_change, src_dir / file_to_change.name)

        with tmp_git_dir(tmp_dir) as git_dir:
            apply_diff(git_diff_file, git_dir)

            actual_git_diff = generate_diff(git_dir)

            assert clean(actual_git_diff) == clean(expected_git_diff)
