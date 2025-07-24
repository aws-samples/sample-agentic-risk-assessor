import json
import boto3
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Manages service JWT tokens for agent-to-agent communication.
    Rotates tokens every 12 hours and stores in Secrets Manager.
    """
    try:
        # Initialize AWS clients
        cognito_client = boto3.client('cognito-idp')
        secrets_client = boto3.client('secretsmanager')
        
        # Get environment variables
        user_pool_id = os.environ['USER_POOL_ID']
        client_id = os.environ['CLIENT_ID']
        secret_arn = os.environ['SECRET_ARN']
        service_username = os.environ['SERVICE_USERNAME']
        service_password = os.environ['SERVICE_PASSWORD']
        
        logger.info(f"Starting service token rotation for user: {service_username}")
        
        # Authenticate service account with Cognito
        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': service_username,
                'PASSWORD': service_password
            }
        )
        
        # Extract JWT token
        jwt_token = auth_response['AuthenticationResult']['AccessToken']
        expires_in = auth_response['AuthenticationResult']['ExpiresIn']
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update secret in Secrets Manager
        secret_value = {
            'token': jwt_token,
            'expires_at': expires_at.isoformat() + 'Z',
            'user_id': service_username,
            'rotated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        secrets_client.update_secret(
            SecretId=secret_arn,
            SecretString=json.dumps(secret_value)
        )
        
        logger.info(f"Service token rotated successfully. Expires at: {expires_at}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Service token rotated successfully',
                'expires_at': expires_at.isoformat() + 'Z'
            })
        }
        
    except Exception as e:
        logger.error(f"Error rotating service token: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to rotate service token',
                'details': str(e)
            })
        }