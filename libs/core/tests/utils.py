from deep_next.core import config

EXAMPLE_REPO_ROOT_DIR = config.ROOT_DIR / "tests" / "_resources" / "example_project"
EXAMPLE_REPO_SRC_DIR = "src"
EXAMPLE_REPO_SRC_PATH = EXAMPLE_REPO_ROOT_DIR / EXAMPLE_REPO_SRC_DIR


def clean(txt: str) -> str:
    return txt.replace(" ", "").replace("\n", "").replace("\\n", "")
