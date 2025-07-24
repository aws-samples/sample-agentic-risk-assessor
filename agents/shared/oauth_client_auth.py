"""OAuth Client Credentials authentication for agents."""

import boto3
import json
import requests
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

class AgentOAuthClient:
    """OAuth Client Credentials authentication for agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.token = None
        self.expires_at = None
        self.client_id = None
        self.client_secret = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load client credentials from Secrets Manager."""
        try:
            secret_name = f"risk-agent-{self.agent_name}-client-secret"
            secrets_client = boto3.client('secretsmanager')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            
            secret_data = json.loads(response['SecretString'])
            self.client_id = secret_data['client_id']
            self.client_secret = secret_data['client_secret']
            
            logger.info(f"Loaded OAuth credentials for agent: {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to load OAuth credentials for {self.agent_name}: {e}")
            raise
    
    def _get_cognito_domain(self) -> str:
        """Get Cognito domain URL."""
        region = os.getenv('AWS_REGION', 'us-east-1')
        domain_prefix = os.environ.get('COGNITO_DOMAIN_PREFIX', 'risk-agent-auth')
        return f"https://{domain_prefix}.auth.{region}.amazoncognito.com"
    
    def authenticate(self) -> str:
        """Get new access token using client credentials."""
        try:
            cognito_domain = self._get_cognito_domain()
            
            response = requests.post(
                f"{cognito_domain}/oauth2/token",
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"OAuth authentication failed: {response.text}")
            
            token_data = response.json()
            self.token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(f"Agent {self.agent_name} authenticated successfully, expires at: {self.expires_at}")
            return self.token
            
        except Exception as e:
            logger.error(f"OAuth authentication failed for {self.agent_name}: {e}")
            raise
    
    def get_valid_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self._token_expired():
            self.authenticate()
        return self.token
    
    def _token_expired(self) -> bool:
        """Check if token is expired or will expire soon."""
        if not self.token or not self.expires_at:
            return True
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))

# Global OAuth clients per agent
_oauth_clients: Dict[str, AgentOAuthClient] = {}

def get_agent_oauth_client(agent_name: str) -> AgentOAuthClient:
    """Get OAuth client for agent."""
    if agent_name not in _oauth_clients:
        _oauth_clients[agent_name] = AgentOAuthClient(agent_name)
    return _oauth_clients[agent_name]

def get_agent_token(agent_name: str) -> str:
    """Get valid token for agent."""
    client = get_agent_oauth_client(agent_name)
    return client.get_valid_token()