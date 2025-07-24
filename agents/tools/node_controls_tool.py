"""
Node Controls Tool - Wraps existing get_node_controls Lambda function
"""
import boto3
import json
from typing import Dict, Any

class NodeControlsTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-get-node-controls-api"
    
    async def get_node_controls(self, project_id: str) -> Dict[str, Any]:
        """Get node controls for a project using existing Lambda"""
        try:
            payload = {
                "requestContext": {"http": {"method": "GET"}},
                "pathParameters": {"id": project_id}
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                return json.loads(result['body'])
            else:
                return {"error": f"Failed to get node controls: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling node controls Lambda: {str(e)}"}