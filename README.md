# Honeywell Temperature Checker

## Overview

The Honeywell Temperature Checker is a simple Python application that monitors the indoor temperatures of devices connected to a Honeywell home automation system. It retrieves the device temperatures at regular intervals and sends an alert if any temperature exceeds a specified threshold.

## Features

- Authenticate and retrieve access tokens from the Honeywell API.
- Periodically refresh the access token using the refresh token.
- Retrieve and parse device temperatures.
- Send alerts via email if a device's temperature exceeds a specified threshold (email to text).
- Log all activities and errors.

## Prerequisites

- Python 3.6 or later
- Docker (for containerization)
- Azure CLI (for Azure Key Vault access and deployment)
- Honeywell Developer Account (for API access)
- SMTP Email Account (for sending alerts)
- User Assigned Managed Identity (UAMI)
- Azure based resource (e.g., VM, ACI, etc) as this app relies on Managed Identity and falls back to a DefaultAzureCredential

### Additional Requirements for Azure Deployment

- Ensure that the UAMI has the necessary permissions for Azure Key Vault.
- Make sure the Azure Container Instance (ACI) is configured to use the UAMI for accessing the secrets from the Key Vault.

## Setup

### Configuration

Create a `config.json` file in the src directory with the following structure:

```json
{
  "keyvault_url": "https://<your-key-vault>.vault.azure.net/",
  "uami_client_id": "<your-uami-client-id>",
  "honeywell": {
    "api_key_secret": "<your-api-key-secret>",
    "client_secret_secret": "<your-client-secret-secret>",
    "username_secret": "<your-username-secret>",
    "password_secret": "<your-password-secret>",
    "redirect_uri": "<your-redirect-uri>",
    "token_url": "https://api.honeywellhome.com/oauth2/token",
    "temperature_threshold": 81
  },
  "email": {
    "smtp_user_secret": "smtp-user",
    "smtp_password_secret": "smtp-app-password",
    "phone_numbers": ["<phone-number-1>", "<phone-number-2>"],
    "carrier_gateway": "txt.att.net",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465
  }
}
```

## Local Execution

Install the required Python packages:

```
# Install the required Python packages
python3 -m pip install -r requirements.txt

# Running the Application
python3 src/honeywell.py
```

## Docker

```
# Building the Docker Image
docker build -t honeywell-temperature-checker .

# Run the Docker Container (assumes running on Azure resource)
Run the Docker Container
```

## Deploy App to Azure and Run

```
# Login to Azure
az login

# Tag the Docker image
docker tag honeywell-temperature-checker <your-acr-name>.azurecr.io/honeywell-temperature-checker:latest

# Push the Docker image to ACR
docker push <your-acr-name>.azurecr.io/honeywell-temperature-checker:latest

# Deploy to ACI
az container create \
  --resource-group <your-resource-group> \
  --name honeywell-temperature-checker \
  --image <your-acr-name>.azurecr.io/honeywell-temperature-checker:latest \
  --assign-identity \
  --registry-login-server <your-acr-name>.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --restart-policy Always
```
