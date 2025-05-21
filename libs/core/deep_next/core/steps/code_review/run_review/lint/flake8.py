import re
import subprocess
from pathlib import Path

from deep_next.core.steps.code_review.run_review.code_reviewer import CodeReviewContext
from unidiff.patch import PatchSet


class Flake8CodeReviewer:
    @property
    def name(self) -> str:
        return "flake8_code_reviewer"

    errs_to_check = [
        "E999",  # SyntaxError or other parsing error (e.g., missing colon, unmatched bracket)  # noqa: E501
        "F821",  # Undefined name (e.g., using a variable that hasn't been defined)
        "F822",  # Undefined name in __all__ (usually breaks module exports)
        "F823",  # Local variable referenced before assignment (common logic error)
    ]

    def _run_linter(self, root_path: Path) -> list[tuple[Path, int, str]]:
        select_msg = ",".join(self.errs_to_check)

        result = subprocess.run(
            ["flake8", f"--select={select_msg}", "."],
            text=True,
            capture_output=True,
            cwd=root_path,
        )

        raw_lines = result.stdout.splitlines()

        pattern = re.compile(r"^(.*?):(\d+):\d+: \w+ .*$")
        results = []
        for raw_line in raw_lines:
            match = pattern.match(raw_line)
            file_path = match.group(1)
            line_number = match.group(2)
            results.append((Path(file_path), int(line_number), raw_line))

        return results

    def _lines_changed(self, git_diff: str) -> dict[Path, list[int]]:

        lines_changed: dict[Path, list[int]] = {}
        for patch in PatchSet(git_diff):
            lines_changed[Path(patch.path)] = [
                line.target_line_no for hunk in patch for line in hunk
            ]

        return lines_changed

    def run(
        self,
        context: CodeReviewContext,
    ) -> list[str]:
        """Run flake8 on the given code and return the issues found."""
        linter_results = self._run_linter(context.root_path)

        lines_changed = self._lines_changed(context.git_diff)

        return [
            issue
            for file_path, line, issue in linter_results
            if file_path in lines_changed and line in lines_changed[file_path]
        ]
