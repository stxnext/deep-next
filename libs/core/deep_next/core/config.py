from enum import Enum
from pathlib import Path

from deep_next.common.config import MONOREPO_DATA_PATH

SRC_DIR = Path(__file__).resolve().parent  # 🛠core/deep_next/core
ROOT_DIR = SRC_DIR.parent.parent  # 🛠core

DATA_DIR = MONOREPO_DATA_PATH / "core"
DATA_DIR.mkdir(exist_ok=True, parents=True)

AUTOMATED_CODE_REVIEW_MAX_ATTEMPTS = 1


class ImplementationModes(str, Enum):
    SINGLE_FILE = "single_file"
    ALL_AT_ONCE = "all_at_once"


# The mode of implementation for the project.
# SINGLE_FILE: one file at a time
# ALL_AT_ONCE: all files at the same time
IMPLEMENTATION_MODE = ImplementationModes.ALL_AT_ONCE


class SRFConfig:
    N_CYCLES = 3
    CYCLE_ITERATION_LIMIT = 20


class SRSConfig:
    N_CYCLES = 3
    CONTEXT_WINDOW = 10


SRF_INDEXER_IGNORE_DIR_PREFIXES = [
    ".venv",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "___",
]
