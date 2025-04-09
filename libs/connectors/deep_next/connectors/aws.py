import boto3
from loguru import logger


def get_default_region():
    """Get the default region.

    Default region is defined by the AWS CLI configuration:
    - global env `AWS_DEFAULT_REGION`
    - or AWS config file `~/.aws/config`
    """
    session = boto3.Session()
    region = session.region_name
    return region


class AWSSecretsManager:
    """AWS SecretsManager connector."""

    def __init__(self):
        logger.debug(f"AWS SecretsManager region: '{get_default_region()}'")
        self.client = boto3.client("secretsmanager")

    def create_secret(self, secret_name, secret_value, overwrite: bool = False) -> str:
        """Create a new secret."""
        try:
            self.client.create_secret(Name=secret_name, SecretString=secret_value)
            logger.debug(f"Secret '{secret_name}' created successfully")
        except self.client.exceptions.ResourceExistsException:
            logger.warning(f"Secret '{secret_name}' already exists")
            if overwrite:
                logger.warning(f"Overwriting secret '{secret_name}'.")
                self.client.update_secret(
                    SecretId=secret_name, SecretString=secret_value
                )
                logger.debug(f"Secret '{secret_name}' updated successfully.")

        return secret_name

    def get_secret(self, secret_name: str) -> str:
        """Retrieve a secret."""
        response = self.client.get_secret_value(SecretId=secret_name)
        logger.debug(f"Retrieved secret: '{secret_name}'")

        return response["SecretString"]

    def delete_secret(self, secret_name: str) -> str:
        """Delete a secret."""
        response = self.client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True,
        )
        logger.debug(f"Deleted secret: '{secret_name}'")

        return response["Name"]
