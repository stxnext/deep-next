import subprocess
from pathlib import Path

from deep_next.common.cmd import RunCmdError, run_command
from loguru import logger


class GitRepositoryError(Exception):
    """Git repository error."""


class BranchExistsError(GitRepositoryError):
    """Branch already exists error."""


class BranchCheckoutError(GitRepositoryError):
    """Branch checkout error."""


def setup_local_git_repo(repo_dir: Path, clone_url: str) -> "GitRepository":
    """Creates git repository if not exists, otherwise gets from repo pool."""
    if repo_dir.exists():
        logger.info(f"Using existing git repository: {repo_dir}")
        return GitRepository(repo_dir)

    return GitRepository.from_git_clone(url=clone_url, output_dir=repo_dir)


class FeatureBranch:
    def __init__(self, ref_branch: str, name: str, git_repo: "GitRepository"):
        self.ref_branch = ref_branch
        self.name = name

        self._git_repo = git_repo

    def commit_all(self, commit_msg: str) -> None:
        logger.info(f"Committing all changes from '{self.name}'...")
        self._git_repo.checkout_branch(self.name)
        self._git_repo.commit_all(commit_msg)

        logger.info("Committed all changes.")

    def push_to_remote(self) -> None:
        logger.info(f"Pushing to remote: '{self.name}'...")
        self._git_repo.push_to_remote(self.name)

        logger.success(f"Pushed changes to remote: '{self.name}'")


# TODO: In evaluation similar git handler is used. It's refactor suggestion.
class GitRepository:
    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir

        if not (repo_dir / ".git").exists():
            raise ValueError(
                f"Provided invalid git repo dir ('.git' not found): {repo_dir}"
            )

    def new_feature_branch(self, ref_branch: str, feature_branch: str) -> FeatureBranch:
        logger.info(
            f"Attempting to create new feature branch '{feature_branch}' "
            f"from '{ref_branch}'..."
        )

        if self.branch_exists(feature_branch):
            raise BranchExistsError(
                f"Branch '{feature_branch}' already exists in '{self.repo_dir}'"
            )

        try:
            run_command(["git", "fetch", "origin", ref_branch], cwd=self.repo_dir)
            run_command(
                ["git", "checkout", "-B", feature_branch, f"origin/{ref_branch}"],
                cwd=self.repo_dir,
            )
        except RunCmdError as e:
            raise BranchCheckoutError(
                f"Failed to create '{feature_branch}' branch in '{self.repo_dir}': {e}"
            ) from e

        self._reset_and_clean_working_directory()

        return FeatureBranch(
            ref_branch=ref_branch,
            name=feature_branch,
            git_repo=self,
        )

    def _reset_and_clean_working_directory(self) -> None:
        """Reset and clean the working directory to ensure a clean state."""
        try:
            run_command(["git", "reset", "--hard"], cwd=self.repo_dir)
            run_command(["git", "clean", "-fd"], cwd=self.repo_dir)

            if not self._is_working_directory_clean():
                raise GitRepositoryError(
                    f"Working directory is not clean in '{self.repo_dir}'"
                )

        except RunCmdError as e:
            raise GitRepositoryError(
                f"Failed to reset and clean working directory in '{self.repo_dir}': {e}"
            ) from e

    def _is_working_directory_clean(self) -> bool:
        """Check if the working directory is clean."""
        status = run_command(["git", "status", "--porcelain"], cwd=self.repo_dir)
        return bool(status.strip())

    def checkout_branch(self, branch: str) -> None:
        """Checkout branch."""
        if not self.branch_exists(branch):
            raise BranchCheckoutError(
                f"Branch '{branch}' does not exist in '{self.repo_dir}'"
            )

        if self.current_branch() == branch:
            logger.info(f"Already on '{branch}' branch")
            return

        try:
            run_command(["git", "checkout", branch], cwd=self.repo_dir)
        except subprocess.CalledProcessError as e:
            raise BranchCheckoutError(
                f"Failed to checkout to '{branch}' branch in '{self.repo_dir}': {e}"
            ) from e

        if not self.current_branch() == branch:
            raise BranchCheckoutError(
                f"Failed to checkout to '{branch}' branch in '{self.repo_dir}'"
            )

    def current_branch(self) -> str:
        """Get current branch."""
        return run_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_dir,
        )

    def branch_exists(self, branch: str) -> bool:
        """Checks if a Git branch exists in the repository."""
        try:
            run_command(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=self.repo_dir,
            )
            return True
        except RunCmdError:
            return False

    def commit_all(self, commit_msg: str):
        """Commits all changes."""
        run_command(["git", "status"], cwd=self.repo_dir)
        run_command(["git", "add", "--all"], cwd=self.repo_dir)
        run_command(
            ["git", "commit", "-m", commit_msg],
            cwd=self.repo_dir,
        )

    def push_to_remote(self, branch: str):
        """Push to remote."""
        self.checkout_branch(branch)
        run_command(
            ["git", "push", "--set-upstream", "origin", branch], cwd=self.repo_dir
        )

    @classmethod
    def from_git_clone(cls, url: str, output_dir: Path) -> "GitRepository":
        """Clone repository."""
        logger.info(f"Cloning repo from '{url}' into '{str(output_dir)}'")
        run_command(["git", "clone", url, str(output_dir)])

        logger.success(f"Successfully cloned repository: {str(output_dir)}")

        return cls(output_dir)
