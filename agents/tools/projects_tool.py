"""
Projects Tool - Wraps existing projects Lambda function
"""
import boto3
import json
from typing import Dict, Any

class ProjectsTool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lambda_client = boto3.client('lambda')
        self.function_name = f"{config.get('project_name', 'risk-agent')}-projects"
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details using existing projects Lambda"""
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
                return {"error": f"Failed to get project: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling projects Lambda: {str(e)}"}
    
    async def list_projects(self) -> Dict[str, Any]:
        """List all projects using existing projects Lambda"""
        try:
            payload = {
                "requestContext": {"http": {"method": "GET"}}
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                return json.loads(result['body'])
            else:
                return {"error": f"Failed to list projects: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling projects Lambda: {str(e)}"}
    
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new project using existing projects Lambda"""
        try:
            payload = {
                "requestContext": {"http": {"method": "POST"}},
                "body": json.dumps(project_data)
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 201:
                return json.loads(result['body'])
            else:
                return {"error": f"Failed to create project: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling projects Lambda: {str(e)}"}