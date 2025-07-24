"""
Service Controls Tool - Wraps existing process_service_controls Lambda function
"""
import boto3
import json
from typing import Dict, Any

class ServiceControlsTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-process-service-controls"
    
    async def process_service_controls(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process service controls using existing process_service_controls Lambda"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(service_data)
            )
            
            result = json.loads(response['Payload'].read())
            return result
                
        except Exception as e:
            return {"error": f"Error calling service controls Lambda: {str(e)}"}