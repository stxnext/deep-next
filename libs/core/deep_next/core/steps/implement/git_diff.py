import subprocess
from pathlib import Path


def is_git_repo(dir_path: Path) -> bool:
    """Check if a given directory is the root of a Git repository."""
    directory = dir_path.resolve()
    git_dir = directory / ".git"

    return git_dir.is_dir()


def apply_diff(git_diff: Path, repo_root: Path) -> None:
    """Applies a diff file to the specified repository root using `git apply`."""
    repo_root = Path(repo_root).resolve()
    git_diff = Path(git_diff).resolve()

    if not repo_root.is_dir():
        raise FileNotFoundError(f"Repository root '{repo_root}' does not exist.")

    if not git_diff.is_file():
        raise FileNotFoundError(f"Diff file '{git_diff}' does not exist.")

    subprocess.run(
        ["git", "apply", str(git_diff)],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def generate_diff(git_repo_root_dir: Path) -> str:
    """Generate a .diff using `git diff` in the specified repository directory."""
    git_repo_root_dir = Path(git_repo_root_dir).resolve()
    if not git_repo_root_dir.is_dir():
        raise FileNotFoundError(
            f"Git repository root directory '{git_repo_root_dir}' does not exist."
        )

    if not is_git_repo(git_repo_root_dir):
        raise FileNotFoundError(f"`.git` not found in directory: `{git_repo_root_dir}`")

    result = subprocess.run(
        ["git", "diff"],
        cwd=git_repo_root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    return result.stdout
