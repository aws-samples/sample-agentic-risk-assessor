"""
Services Tool - Wraps existing read_services Lambda function
"""
import boto3
import json
from typing import Dict, Any

class ServicesTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-read-services"
    
    async def read_services(self) -> Dict[str, Any]:
        """Read services using existing read_services Lambda"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps({})
            )
            
            result = json.loads(response['Payload'].read())
            return result
                
        except Exception as e:
            return {"error": f"Error calling read services Lambda: {str(e)}"}