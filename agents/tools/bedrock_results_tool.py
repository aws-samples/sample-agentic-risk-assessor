"""
Bedrock Results Tool - Wraps existing process_bedrock_results Lambda function
"""
import boto3
import json
from typing import Dict, Any

class BedrockResultsTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-process-bedrock-results"
    
    async def process_bedrock_results(self, results_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Bedrock results using existing process_bedrock_results Lambda"""
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(results_data)
            )
            
            result = json.loads(response['Payload'].read())
            return result
                
        except Exception as e:
            return {"error": f"Error calling process Bedrock results Lambda: {str(e)}"}