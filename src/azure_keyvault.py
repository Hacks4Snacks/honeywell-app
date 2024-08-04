from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ClientAuthenticationError
import logging


def get_secret_from_key_vault(keyvault_name, secret_name, client_id=None):
    """
    Retrieves a secret from Azure Key Vault.
    Parameters:
    - keyvault_name (str): The name or URL of the Azure Key Vault.
    - secret_name (str): The name of the secret to retrieve.
    - client_id (str, optional): The client ID for authentication. If not provided, Managed Identity Credential will be used.
    Returns:
    - str: The value of the retrieved secret.
    """
    credential = None

    if client_id:
        try:
            credential = ManagedIdentityCredential(client_id=client_id)
            client = SecretClient(vault_url=keyvault_name, credential=credential)
            secret = client.get_secret(secret_name)
            return secret.value
        except ClientAuthenticationError as e:
            logging.error(f"Managed Identity authentication with client_id {client_id} failed: {e}")
            # Fall back to DefaultAzureCredential
            logging.info("Falling back to DefaultAzureCredential for authentication.")

    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_name, credential=credential)
        secret = client.get_secret(secret_name)
        return secret.value
    except ClientAuthenticationError as e:
        logging.error(f"Default authentication methods failed: {e}")
        raise