from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodePatch:
    file_path: Path
    before: str
    after: str
    error_type: str | None = None
    diff: str = ""
