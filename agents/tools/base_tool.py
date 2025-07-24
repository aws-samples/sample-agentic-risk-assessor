"""
Base Tool Class with automatic credential refresh
"""
import boto3
import json
from typing import Dict, Any
from botocore.exceptions import ClientError

class BaseTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._lambda_client = None
    
    @property
    def lambda_client(self):
        if self._lambda_client is None:
            self._lambda_client = boto3.client('lambda')
        return self._lambda_client
    
    def _refresh_credentials(self):
        """Refresh AWS credentials by creating new client"""
        self._lambda_client = boto3.client('lambda')
    
    async def _invoke_lambda_with_retry(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Lambda with automatic retry on expired token"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(payload)
            )
            return json.loads(response['Payload'].read())
        except ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                # Refresh credentials and retry once
                self._refresh_credentials()
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    Payload=json.dumps(payload)
                )
                return json.loads(response['Payload'].read())
            raise e