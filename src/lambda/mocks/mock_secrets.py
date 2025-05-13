import json
import logging
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock secrets for testing
MOCK_SECRETS = {
    "HRIM/OpenAI/ApiKey": json.dumps({
        "api_key": "sk-mock-openai-api-key-for-testing-purposes-only"
    }),
    "HRIM/WhatsApp/ApiKey": json.dumps({
        "api_url": "https://graph.facebook.com/v18.0/mock-phone-id/messages",
        "access_token": "mock-whatsapp-access-token-for-testing"
    })
}

class MockSecretsManager:
    """Mock implementation of AWS Secrets Manager client."""
    
    @staticmethod
    def get_secret_value(SecretId):
        """
        Simulate getting a secret from AWS Secrets Manager.
        
        Args:
            SecretId (str): Secret identifier
            
        Returns:
            dict: Mock response with SecretString
            
        Raises:
            ClientError: If the secret doesn't exist in the mock store
        """
        logger.info(f"MOCK SECRETS MANAGER: Getting secret {SecretId}")
        
        # Check if the secret exists in our mock store
        if SecretId in MOCK_SECRETS:
            return {
                "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{SecretId}",
                "Name": SecretId,
                "VersionId": "mock-version-id",
                "SecretString": MOCK_SECRETS[SecretId],
                "VersionStages": ["AWSCURRENT"],
                "CreatedDate": "2021-01-01T00:00:00.000Z"
            }
        
        # Add support for partial matching on secret name prefixes
        for secret_id in MOCK_SECRETS:
            if SecretId in secret_id:
                logger.info(f"Found partial match: {secret_id}")
                return {
                    "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{secret_id}",
                    "Name": secret_id,
                    "VersionId": "mock-version-id",
                    "SecretString": MOCK_SECRETS[secret_id],
                    "VersionStages": ["AWSCURRENT"],
                    "CreatedDate": "2021-01-01T00:00:00.000Z"
                }
        
        # Secret not found
        logger.error(f"Secret {SecretId} not found in mock store")
        raise ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": f"Secrets Manager can't find the specified secret: {SecretId}"
                }
            },
            "GetSecretValue"
        )
    
    @staticmethod
    def create_secret(Name, Description, SecretString):
        """
        Simulate creating a secret in AWS Secrets Manager.
        
        Args:
            Name (str): Secret name
            Description (str): Secret description
            SecretString (str): Secret value
            
        Returns:
            dict: Mock response with ARN and Name
        """
        logger.info(f"MOCK SECRETS MANAGER: Creating secret {Name}")
        
        # Add the secret to our mock store
        MOCK_SECRETS[Name] = SecretString
        
        return {
            "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{Name}",
            "Name": Name,
            "VersionId": "mock-version-id"
        }

def get_mock_secrets_manager_client():
    """Return a mock Secrets Manager client instance."""
    return MockSecretsManager 