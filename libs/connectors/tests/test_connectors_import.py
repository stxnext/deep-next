def test_success() -> None:
    assert True


def test_root_installed_ok() -> None:
    from deep_next.connectors.version_control_provider import BaseConnector

    assert BaseConnector
