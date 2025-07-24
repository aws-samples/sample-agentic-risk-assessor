"""
Diagram Analysis Tool - Wraps existing diagram_analysis Lambda function
"""
from typing import Dict, Any
from .base_tool import BaseTool

class DiagramAnalysisTool(BaseTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.function_name = f"{config.get('project_name', 'risk-agent')}-diagram_analysis"
    
    async def analyze_diagram(self, project_id: str) -> Dict[str, Any]:
        """Analyze diagram using existing diagram_analysis Lambda"""
        try:
            payload = {
                "requestContext": {"http": {"method": "POST"}},
                "pathParameters": {"id": project_id}
            }
            
            result = await self._invoke_lambda_with_retry(self.function_name, payload)
            
            if result.get('statusCode') == 200:
                return json.loads(result['body'])
            else:
                return {"error": f"Analysis failed: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling diagram analysis Lambda: {str(e)}"}
    
    async def get_analysis(self, project_id: str) -> Dict[str, Any]:
        """Get existing analysis using diagram_analysis Lambda"""
        try:
            payload = {
                "requestContext": {"http": {"method": "GET"}},
                "pathParameters": {"id": project_id}
            }
            
            result = await self._invoke_lambda_with_retry(self.function_name, payload)
            
            if result.get('statusCode') == 200:
                return json.loads(result['body'])
            else:
                return {"error": f"Failed to get analysis: {result.get('body', 'Unknown error')}"}
                
        except Exception as e:
            return {"error": f"Error calling diagram analysis Lambda: {str(e)}"}