import pytest
from dotenv import load_dotenv

load_dotenv()


def pytest_collection_modifyitems(items):
    """All tests marked as `llm` (`@pytest.mark.llm`) have more tries to succeed."""
    rerun_count = 2
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(pytest.mark.flaky(reruns=rerun_count))
