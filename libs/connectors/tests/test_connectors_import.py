def test_success() -> None:
    assert True


def test_root_installed_ok() -> None:
    from deep_next.connectors.aws import AWSSecretsManager
    from deep_next.connectors.gitlab_connector import GitLabConnector

    assert AWSSecretsManager
    assert GitLabConnector
