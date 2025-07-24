"""
Auto-refreshing credentials for agents
"""
import boto3
import os
from datetime import datetime
from botocore.credentials import CredentialProvider, RefreshableCredentials
from botocore.session import get_session

class AssumeRoleCredentialProvider(CredentialProvider):
    METHOD = 'assume-role-auto-refresh'
    
    def __init__(self, role_arn, session_name):
        self.role_arn = role_arn
        self.session_name = session_name
        # Use default credentials in ECS (IAM role attached to task)
        self._sts_client = boto3.client('sts')
        self.refresh_count = 0
    
    def load(self):
        def refresh():
            self.refresh_count += 1
            print(f"🔄 [{self.session_name}] Credential refresh #{self.refresh_count}")
            
            response = self._sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName=f"{self.session_name}-{int(datetime.now().timestamp())}"
            )
            credentials = response['Credentials']
            
            return {
                'access_key': credentials['AccessKeyId'],
                'secret_key': credentials['SecretAccessKey'],
                'token': credentials['SessionToken'],
                'expiry_time': credentials['Expiration'].isoformat()
            }
        
        return RefreshableCredentials.create_from_metadata(
            metadata=refresh(),
            refresh_using=refresh,
            method=self.METHOD
        )

def create_auto_refreshing_session(agent_name):
    """Create boto3 session with auto-detected role assumption"""
    bedrock_role_arn = os.getenv('BEDROCK_ROLE_ARN')
    
    if not bedrock_role_arn:
        return boto3.Session()
    
    # Get current account ID
    sts_client = boto3.client('sts')
    current_account = sts_client.get_caller_identity()['Account']
    
    # Extract account ID from bedrock role ARN
    bedrock_account = bedrock_role_arn.split(':')[4]
    
    # If same account, use direct credentials
    if current_account == bedrock_account:
        return boto3.Session()
    
    # If cross-account, assume role
    else:
        session = get_session()
        provider = AssumeRoleCredentialProvider(
            role_arn=bedrock_role_arn,
            session_name=f'{agent_name}-agent'
        )
        session.get_component('credential_provider').insert_before('env', provider)
        return boto3.Session(botocore_session=session)