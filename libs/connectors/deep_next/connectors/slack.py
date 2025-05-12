import os
from functools import wraps
from typing import Any, Callable

import click
from loguru import logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_NOTIFICATIONS_ENV_NAME = "SLACK_NOTIFICATIONS"
SLACK_CHANNEL_ENV_NAME = "SLACK_CHANNEL"
SLACK_BOT_TOKEN_ENV_NAME = "SLACK_BOT_TOKEN"


class SlackConnectorError(Exception):
    """Custom exception for SlackConnector"""


class SlackConnector:
    def __init__(self, token: str | None = None, channel: str | None = None) -> None:
        """Initializes Slack connector.

        Parameters:
            token: Slack bot token.
            channel: Slack channel ID or name.
        """
        self.token = token or os.environ[SLACK_BOT_TOKEN_ENV_NAME]
        self.channel = channel or os.environ[SLACK_CHANNEL_ENV_NAME]

        self.client = WebClient(token=self.token, timeout=30)

    def post(self, message: str) -> None:
        """Post a message to the Slack channel"""
        try:
            self.client.chat_postMessage(channel=self.channel, text=message)
            logger.info(f"Slack notification sent: \n{message}")
        except SlackApiError as e:
            raise SlackConnectorError(f"Slack API Error: {e}") from None
        except Exception as e:
            raise SlackConnectorError(f"Unexpected error: {e}") from None


def slack_notifications(func: Callable) -> Callable:
    def assert_env_vars():
        for env_var in [SLACK_BOT_TOKEN_ENV_NAME, SLACK_CHANNEL_ENV_NAME]:
            if not os.getenv(env_var):
                raise SlackConnectorError(f"Missing env var: '{env_var}'")

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        slack_connector = None
        slack_enabled = (
            os.getenv(SLACK_NOTIFICATIONS_ENV_NAME, "false").lower() == "true"
        )
        logger.debug(
            f"Enabled Slack notifications for `{func.__name__}` func: '{slack_enabled}'"
        )

        if slack_enabled:
            assert_env_vars()

            try:
                slack_connector = SlackConnector()
                slack_connector.post(f"🚀 Starting `{func.__name__}`")
            except Exception as e:
                logger.warning(f"Slack initial notification skipped due to error: {e}")

        try:
            result = func(*args, **kwargs)

            if slack_enabled and slack_connector:
                message = f"🟢 `{func.__name__}` completed successfully"

                try:
                    slack_connector.post(message)
                except SlackConnectorError as e:
                    logger.warning(
                        f"Slack success notification skipped due to error: {e}"
                    )

            return result

        except Exception as e:
            if slack_enabled and slack_connector:
                message = f"🔴 `{func.__name__}` failed! Error: {e}"

                try:
                    slack_connector.post(message)
                except SlackConnectorError as e:
                    logger.warning(
                        f"Slack error notification skipped due to error: {e}"
                    )

            raise

    return wrapper


@click.command()
@click.option(
    "--token",
    "-t",
    envvar=SLACK_BOT_TOKEN_ENV_NAME,
    required=True,
    help=f"Slack Bot Token. Defaults to '{SLACK_BOT_TOKEN_ENV_NAME}' env var.",
)
@click.option(
    "--channel",
    "-ch",
    envvar=SLACK_CHANNEL_ENV_NAME,
    required=True,
    help=f"Slack Channel ID or name. Defaults to '{SLACK_CHANNEL_ENV_NAME}' env var.",
)
@click.option("--message", "-msg", required=True, help="Message to send")
def cli(token, channel, message):
    """CLI to send a message to a Slack channel using SlackConnector."""
    try:
        slack_connector = SlackConnector(token=token, channel=channel)
        slack_connector.post(message=message)
    except SlackConnectorError as e:
        logger.error(f"SlackConnectorError: {e}")
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
    else:
        click.echo(f"Message successfully sent to channel '{channel}'.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    cli()
