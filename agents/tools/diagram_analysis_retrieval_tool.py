"""
Diagram Analysis Retrieval Tool - Wraps existing diagram_analysis Lambda for GET operations
"""
import boto3
import json
from typing import Dict, Any

class DiagramAnalysisRetrievalTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-diagram_analysis"
    
    async def get_diagram_analysis(self, project_id: str) -> Dict[str, Any]:
        """Get existing diagram analysis for a project using existing Lambda"""
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
                return {"error": f"Failed to get diagram analysis: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling diagram analysis Lambda: {str(e)}"}