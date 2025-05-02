from pathlib import Path
import os

from deep_next.common.common import gitignore_name

MONOREPO_ROOT_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent

MONOREPO_DATA_PATH = MONOREPO_ROOT_PATH / gitignore_name("data")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
