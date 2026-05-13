"""
Examples demonstrating the axiompy secrets management module.

Shows how to:
- Use different secret backends
- Handle errors with Result types
- Work with credentials and auth tokens
- Implement environment-specific configuration
"""


# Example 1: Basic Cerberus Usage
def example_cerberus_basic():
    """Retrieve a secret from Cerberus."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(
        vault_path="shared/database/mysql",
        cerberus_url="https://cerberus.example.com",
        cerberus_region="us-west-2",
    )

    result = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings)

    if result.is_ok():
        client = result.unwrap()
        secret_result = client.get_secret("password")
        password = secret_result.unwrap_or("default_password")
        print(f"Password: {password}")
    else:
        print(f"Error: {result.get_error()}")


# Example 2: Error Handling with Railway-Oriented Programming
def example_rop_error_handling():
    """Use Railway-Oriented Programming for error handling."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)

    result = (
        SecretsClientFactory.create(SecretsClientType.CERBERUS, settings)
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
        # Uses default AWS credentials if not specified
    )

    client = SecretsClientFactory.create(SecretsClientType.AWS_SECRETS_MANAGER, settings).unwrap()

    # Get a secret
    db_password = client.get_secret("prod/database/mysql-password").unwrap()

    # Get secrets as dictionary
    db_secrets = client.get_secrets("prod/database/").unwrap()
    for key, value in db_secrets.items():
        print(f"{key}: {value[:10]}...")  # Print first 10 chars

    # Store a secret
    client.put_secret("dev/api/stripe-key", "sk_test_xxxxx").unwrap()

    # Delete a secret
    client.delete_secret("old-secret").unwrap()


# Example 4: AWS KMS for Encryption
def example_aws_kms():
    """Use AWS KMS for encryption/decryption."""
    from axiompy.secrets import AWSKMSSettings, SecretsClientFactory, SecretsClientType

    settings = AWSKMSSettings(
        key_id="arn:aws:kms:us-west-2:111122223333:key/1234abcd-...", region="us-west-2"
    )

    client = SecretsClientFactory.create(SecretsClientType.AWS_KMS, settings).unwrap()

    # Encrypt a value
    plaintext = "my-secret-database-password"
    encrypted_result = client.encrypt(plaintext)
    encrypted = encrypted_result.unwrap()
    print(f"Encrypted: {encrypted[:50]}...")

    # Decrypt the value
    decrypted = client.decrypt(encrypted).unwrap()
    print(f"Decrypted: {decrypted}")


# Example 5: HashiCorp Vault
def example_vault():
    """Use HashiCorp Vault for secrets."""
    from axiompy.secrets import SecretsClientFactory, SecretsClientType, VaultSettings

    settings = VaultSettings(
        vault_addr="https://vault.example.com",
        vault_token="s.xxxxxxxxxxxxxxxx",
        mount_path="secret",
    )

    client = SecretsClientFactory.create(SecretsClientType.VAULT, settings).unwrap()

    # Get secret
    secret = client.get_secret("database/mysql").unwrap()

    # Get all secrets
    secrets = client.get_secrets("database/").unwrap()

    # Store secret
    client.put_secret("app/api-key", "key-value").unwrap()

    # List secrets
    secret_keys = client.list_secrets("database/").unwrap()
    print(f"Available secrets: {secret_keys}")


# Example 6: Azure Key Vault
def example_azure_keyvault():
    """Use Azure Key Vault for secrets."""
    from axiompy.secrets import AzureKeyVaultSettings, SecretsClientFactory, SecretsClientType

    settings = AzureKeyVaultSettings(
        vault_url="https://myvault.vault.azure.net/",
        tenant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        client_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        client_secret="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    client = SecretsClientFactory.create(SecretsClientType.AZURE_KEYVAULT, settings).unwrap()

    # Get secret
    secret = client.get_secret("database-password").unwrap()

    # Store secret
    client.put_secret("app-key", "secret-value").unwrap()

    # List secrets
    secrets = client.list_secrets("database-").unwrap()


# Example 7: Credential Provider - Authentication Tokens
def example_credentials_auth_tokens():
    """Use CredentialProvider for auth tokens."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)
    client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    # Get Databricks auth token
    token_result = client.get_auth_token("databricks/service-token")

    if token_result.is_ok():
        token = token_result.unwrap()
        print(f"Token type: {token.token_type}")
        print(f"Token: {token.token[:20]}...")
        print(f"Authorization header: {str(token)}")


# Example 8: Credential Provider - Database Credentials
def example_credentials_database():
    """Use CredentialProvider for database credentials."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)
    client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    # Get database credentials
    cred_result = client.get_database_credentials("database/mysql")

    if cred_result.is_ok():
        cred = cred_result.unwrap()
        print(f"Username: {cred.username}")
        print(f"Password: {cred.password[:10]}...")

        # Check if expired
        if not cred.is_expired():
            # Use credentials
            import pymysql

            connection = pymysql.connect(
                host="localhost", user=cred.username, password=cred.password, database="mydb"
            )


# Example 9: Environment-Specific Configuration
def example_environment_specific():
    """Use environment variables to switch backends."""
    import os

    from axiompy.secrets import SecretsClientFactory, SecretsClientType

    # Get backend from environment
    backend_name = os.getenv("SECRET_BACKEND", "cerberus").upper()
    client_type = SecretsClientType[backend_name]

    # Load appropriate settings based on backend
    if client_type == SecretsClientType.CERBERUS:
        from axiompy.secrets import CerberusSettings

        settings = CerberusSettings(
            vault_path=os.getenv("CERBERUS_VAULT_PATH"),
            cerberus_url=os.getenv("CERBERUS_URL"),
            cerberus_region=os.getenv("CERBERUS_REGION"),
        )
    elif client_type == SecretsClientType.VAULT:
        from axiompy.secrets import VaultSettings

        settings = VaultSettings(
            vault_addr=os.getenv("VAULT_ADDR"), vault_token=os.getenv("VAULT_TOKEN")
        )
    elif client_type == SecretsClientType.AWS_SECRETS_MANAGER:
        from axiompy.secrets import AWSSecretsManagerSettings

        settings = AWSSecretsManagerSettings(region=os.getenv("AWS_REGION", "us-west-2"))
    else:
        raise ValueError(f"Unsupported backend: {backend_name}")

    # Create client
    client = SecretsClientFactory.create(client_type, settings).unwrap()

    # Use client
    secret = client.get_secret("app/api-key").unwrap()
    print(f"Secret: {secret}")


# Example 10: Credential Caching
def example_credential_caching():
    """Demonstrate credential caching."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)
    client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    # First call hits the vault
    cred1 = client.get_database_credentials("database/mysql").unwrap()

    # Second call uses cache
    cred2 = client.get_database_credentials("database/mysql").unwrap()

    # Clear cache to force refresh
    client.refresh_credential_cache()

    # Third call hits the vault again
    cred3 = client.get_database_credentials("database/mysql").unwrap()


# Example 11: Integration with Databricks API
def example_databricks_integration():
    """Use credentials to authenticate with Databricks."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)
    client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    # Get Databricks token
    token = client.get_auth_token("databricks/token").unwrap()

    # Use token for API calls
    import requests

    headers = {"Authorization": str(token)}

    response = requests.get(
        "https://example-workspace.cloud.databricks.com/api/2.0/workspace/list", headers=headers
    )

    workspaces = response.json()
    print(f"Workspaces: {workspaces}")


# Example 12: Error Recovery Patterns
def example_error_recovery():
    """Demonstrate error recovery patterns."""
    from axiompy.secrets import CerberusSettings, SecretsClientFactory, SecretsClientType

    settings = CerberusSettings(...)
    client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    # Pattern 1: Provide fallback
    api_key = (
        client.get_secret("production/api-key")
        .or_else(lambda err: client.get_secret("staging/api-key"))
        .or_else(lambda err: error("No API key available"))
        .unwrap()
    )

    # Pattern 2: Log error but continue
    from axiompy.result import Ok

    api_key = (
        client.get_secret("api-key")
        .map_error(lambda err: (print(f"Warning: {err}"), err)[1])
        .or_else(lambda _: Ok("default-key"))
        .unwrap()
    )

    # Pattern 3: Retry logic
    from axiompy.decorators import Retry

    @Retry(max_attempts=3, delay=1.0)
    def get_secret_with_retry():
        return client.get_secret("critical-secret").unwrap()

    secret = get_secret_with_retry()


if __name__ == "__main__":
    print("Secrets Management Examples")
    print("See function definitions for specific examples")
    print("\nAvailable examples:")
    print("- example_cerberus_basic()")
    print("- example_rop_error_handling()")
    print("- example_aws_secrets_manager()")
    print("- example_aws_kms()")
    print("- example_vault()")
    print("- example_azure_keyvault()")
    print("- example_credentials_auth_tokens()")
    print("- example_credentials_database()")
    print("- example_environment_specific()")
    print("- example_credential_caching()")
    print("- example_databricks_integration()")
    print("- example_error_recovery()")
