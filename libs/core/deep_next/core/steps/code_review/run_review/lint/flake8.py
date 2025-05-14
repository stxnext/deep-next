from pathlib import Path

from deep_next.core.steps.code_review.run_review.code_reviewer import BaseCodeReviewer


class Flake8CodeReviewer(BaseCodeReviewer):
    @property
    def name(self) -> str:
        return "flake8_code_reviewer"

    def run(
        self,
        root_path: Path,
        issue_statement: str,
        project_knowledge: str,
        git_diff: str,
        code_fragments: dict[str, list[str]],
    ) -> list[str]:
        """Run flake8 on the given code and return the issues found."""
        import subprocess

        # Run flake8 on the git diff
        result = subprocess.run(
            ["flake8", "--diff"],
            input=git_diff,
            text=True,
            capture_output=True,
            cwd=root_path,
        )

        # Parse the output and return the issues
        return result.stdout.splitlines()
