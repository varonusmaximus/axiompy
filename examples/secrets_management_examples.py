"""
Examples demonstrating the axiompy secrets management module.

Shows how to:
- Use different secret backends (local .env, AWS Secrets Manager, AWS KMS)
- Handle errors with Result types
- Work with credentials and auth tokens
- Implement environment-specific configuration
"""


# Example 1: Local .env (development)
def example_local_basic():
    """Read a secret from a local .env file."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)

    if result.is_ok():
        client = result.unwrap()
        secret_result = client.get_secret("database_password")
        password = secret_result.unwrap_or("default_password")
        print(f"Password: {password}")
    else:
        print(f"Error: {result.get_error()}")


# Example 2: Error handling with Railway-Oriented Programming
def example_rop_error_handling():
    """Use Railway-Oriented Programming for error handling."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")

    result = (
        SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        .then(lambda client: client.get_secret("db_password"))
        .map(lambda pwd: pwd.strip())
        .map_error(lambda err: f"Failed to retrieve password: {err}")
        .unwrap_or("fallback_password")
    )

    print(f"Password: {result}")


# Example 3: AWS Secrets Manager
def example_aws_secrets_manager():
    """Use AWS Secrets Manager for secrets."""
    from axiompy.secrets import AWSSecretsManagerSettings, SecretsClientFactory, SecretsClientType

    settings = AWSSecretsManagerSettings(
        region="us-west-2",
    )

    client = SecretsClientFactory.create(SecretsClientType.AWS_SECRETS_MANAGER, settings).unwrap()

    db_password = client.get_secret("prod/database/mysql-password").unwrap()

    db_secrets = client.get_secrets("prod/database/").unwrap()
    for key, value in db_secrets.items():
        print(f"{key}: {value[:10]}...")

    client.put_secret("dev/api/stripe-key", "sk_test_xxxxx").unwrap()

    client.delete_secret("old-secret").unwrap()


# Example 4: AWS KMS for encryption
def example_aws_kms():
    """Use AWS KMS for encryption/decryption."""
    from axiompy.secrets import AWSKMSSettings, SecretsClientFactory, SecretsClientType

    settings = AWSKMSSettings(
        key_id="arn:aws:kms:us-west-2:111122223333:key/1234abcd-...", region="us-west-2"
    )

    client = SecretsClientFactory.create(SecretsClientType.AWS_KMS, settings).unwrap()

    plaintext = "my-secret-database-password"
    encrypted_result = client.encrypt(plaintext)
    encrypted = encrypted_result.unwrap()
    print(f"Encrypted: {encrypted[:50]}...")

    decrypted = client.decrypt(encrypted).unwrap()
    print(f"Decrypted: {decrypted}")


# Example 5: Credential provider — auth tokens (local .env)
def example_credentials_auth_tokens():
    """Use CredentialProvider for auth tokens via LOCAL backend."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    token_result = client.get_auth_token("databricks/service-token")

    if token_result.is_ok():
        token = token_result.unwrap()
        print(f"Token type: {token.token_type}")
        print(f"Token: {token.token[:20]}...")
        print(f"Authorization header: {str(token)}")


# Example 6: Credential provider — database credentials
def example_credentials_database():
    """Use CredentialProvider for database credentials."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    cred_result = client.get_database_credentials("database/mysql")

    if cred_result.is_ok():
        cred = cred_result.unwrap()
        print(f"Username: {cred.username}")
        print(f"Password: {cred.password[:10]}...")

        if not cred.is_expired():
            print("(connect with your DB driver here)")


# Example 7: Environment-specific configuration
def example_environment_specific():
    """Use environment variables to switch backends."""
    import os

    from axiompy.secrets import (
        AWSSecretsManagerSettings,
        LocalSettings,
        SecretsClientFactory,
        SecretsClientType,
    )

    backend_name = os.getenv("SECRET_BACKEND", "local").lower()
    match backend_name:
        case "local":
            settings = LocalSettings(env_file=os.getenv("ENV_FILE", ".env"))
            client_type = SecretsClientType.LOCAL
        case "aws_secrets_manager":
            settings = AWSSecretsManagerSettings(region=os.getenv("AWS_REGION", "us-west-2"))
            client_type = SecretsClientType.AWS_SECRETS_MANAGER
        case _:
            raise ValueError(f"Unsupported backend: {backend_name}")

    client = SecretsClientFactory.create(client_type, settings).unwrap()
    secret = client.get_secret("app/api-key").unwrap()
    print(f"Secret: {secret}")


# Example 8: Credential caching
def example_credential_caching():
    """Demonstrate credential caching."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    cred1 = client.get_database_credentials("database/mysql").unwrap()
    cred2 = client.get_database_credentials("database/mysql").unwrap()
    client.refresh_credential_cache()
    cred3 = client.get_database_credentials("database/mysql").unwrap()
    assert cred1.username == cred2.username == cred3.username


# Example 9: Databricks-style token from local .env
def example_databricks_integration():
    """Use credentials to authenticate with an HTTP API."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    token = client.get_auth_token("databricks/token").unwrap()

    import requests

    headers = {"Authorization": str(token)}
    response = requests.get(
        "https://example-workspace.cloud.databricks.com/api/2.0/workspace/list",
        headers=headers,
        timeout=30,
    )
    print(f"Status: {response.status_code}")


# Example 10: Error recovery patterns
def example_error_recovery():
    """Demonstrate error recovery patterns."""
    from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    from axiompy.result import Err

    api_key = (
        client.get_secret("production/api-key")
        .or_else(lambda err: client.get_secret("staging/api-key"))
        .or_else(lambda _err: Err("No API key available"))
        .unwrap()
    )
    print(api_key)

    from axiompy.result import Ok

    api_key = (
        client.get_secret("api-key")
        .map_error(lambda err: (print(f"Warning: {err}"), err)[1])
        .or_else(lambda _: Ok("default-key"))
        .unwrap()
    )
    print(api_key)

    from axiompy.decorators import Retry

    @Retry(max_attempts=3, delay=1.0)
    def get_secret_with_retry() -> str:
        return client.get_secret("critical-secret").unwrap()

    secret = get_secret_with_retry()
    print(secret)


if __name__ == "__main__":
    print("Secrets Management Examples")
    print("See function definitions for specific examples")
    print("\nAvailable examples:")
    print("- example_local_basic()")
    print("- example_rop_error_handling()")
    print("- example_aws_secrets_manager()")
    print("- example_aws_kms()")
    print("- example_credentials_auth_tokens()")
    print("- example_credentials_database()")
    print("- example_environment_specific()")
    print("- example_credential_caching()")
    print("- example_databricks_integration()")
    print("- example_error_recovery()")
