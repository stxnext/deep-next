from pathlib import Path
import subprocess

from deep_next.core.steps.code_review.run_review.code_reviewer import BaseCodeReviewer


class Flake8CodeReviewer(BaseCodeReviewer):
    @property
    def name(self) -> str:
        return "flake8_code_reviewer"

    errs_to_ignore = [
        "E501",  # Line too long
        "E722",  # Do not use bare except
        "E731",  # Do not assign a lambda expression, use a def
        "E741",  # Ambiguous variable name
        "E722",  # Do not use bare except
        "W503",  # Line break before binary operator
    ]

    def run(
        self,
        root_path: Path,
        issue_statement: str,
        project_knowledge: str,
        git_diff: str,
        code_fragments: dict[str, list[str]],
    ) -> list[str]:
        """Run flake8 on the given code and return the issues found."""

        ignore_msg = ",".join(self.errs_to_ignore)

        result = subprocess.run(
            ["flake8", "--select=E,F", f"--ignore={ignore_msg}", "."],
            text=True,
            capture_output=True,
            cwd=root_path,
        )

        # Parse the output and return the issues
        return result.stdout.splitlines()
