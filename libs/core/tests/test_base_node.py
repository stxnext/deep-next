from contextlib import contextmanager
from io import StringIO

from deep_next.core.base_node import BaseNode
from loguru import logger


@contextmanager
def capture_loguru_logs():
    """Capture loguru logs to a str for testing."""
    try:
        logger.remove()
        log_output = StringIO()
        logger.add(log_output, format="{message}")
        yield log_output
    finally:
        logger.remove()


def test_base_node_logging():
    msg = "example_method msg"
    msg_static = "example_static_method msg"

    class TestNode(BaseNode):
        def example_method(self):
            logger.info(msg)

        @staticmethod
        def example_static_method():
            logger.info(msg_static)

    node = TestNode()
    with capture_loguru_logs() as log_output:
        node.example_method()
        node.example_static_method()

        log_contents = log_output.getvalue()

    assert "Executing 'Example Method'" in log_contents
    assert msg in log_contents

    assert "Executing 'Example Static Method'" in log_contents
    assert msg_static in log_contents
