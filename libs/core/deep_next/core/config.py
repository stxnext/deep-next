from pathlib import Path

from deep_next.common.config import MONOREPO_DATA_PATH

SRC_DIR = Path(__file__).resolve().parent  # 🛠core/deep_next/core
ROOT_DIR = SRC_DIR.parent.parent  # 🛠core

DATA_DIR = MONOREPO_DATA_PATH / "core"
DATA_DIR.mkdir(exist_ok=True, parents=True)


class SRFConfig:
    N_CYCLES = 1
    CYCLE_ITERATION_LIMIT = 5


class SRSConfig:
    N_CYCLES = 1
    CONTEXT_WINDOW = 10


SRF_INDEXER_IGNORE_DIR_PREFIXES = [
    ".venv",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "___",
]
