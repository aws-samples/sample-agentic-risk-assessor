"""
Bedrock Tool - Wraps existing invoke_bedrock Lambda function
"""
import boto3
import json
from typing import Dict, Any

class BedrockTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-invoke-bedrock"
    
    async def invoke_bedrock(self, service: str, prompt: str) -> Dict[str, Any]:
        """Invoke Bedrock using existing invoke_bedrock Lambda"""
        try:
            payload = {
                "service": service,
                "prompt": prompt
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result
                
        except Exception as e:
            return {"error": f"Error calling Bedrock Lambda: {str(e)}"}