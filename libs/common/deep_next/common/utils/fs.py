import shutil
import subprocess
import tempfile
import traceback
from contextlib import contextmanager
from pathlib import Path

from deep_next.core.steps.implement.git_diff import is_git_repo


@contextmanager
def create_temp_dir() -> Path:
    """Context manager to create a temporary directory.

    The directory is automatically removed after exiting the context.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        yield tmp_dir
    finally:
        shutil.rmtree(tmp_dir)


@contextmanager
def tmp_git_dir(dir_path: Path | str = "."):
    """Context manager that creates a temporary `.git` directory in the specified path.

    Commits all changes with the message "initial state", and removes the `.git`
    directory when done.
    """
    dir_path = Path(dir_path).resolve()

    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory '{dir_path}' does not exist.")

    if is_git_repo(dir_path):
        raise FileExistsError(
            f"The directory '{dir_path}' is already a Git repository."
        )

    with create_temp_dir() as tmp_dir:
        git_dir = tmp_dir / dir_path.name
        shutil.copytree(dir_path, git_dir)
        try:
            subprocess.run(
                ["git", "init"],
                cwd=git_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=git_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["git", "commit", "-m", "initial state"],
                cwd=git_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            yield git_dir
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            print(f"Command: {e.cmd}")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.output}")
            print(f"Error Output: {e.stderr}")
            traceback.print_exc()
            raise
