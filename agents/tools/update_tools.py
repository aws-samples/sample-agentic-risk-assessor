"""
Update Tools for Node and Flow Management
"""
import boto3
import json
from typing import Dict, Any
from .base_tool import BaseTool

class UpdateNodeTool(BaseTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.function_name = 'risk-agent-update-node-api'
    
    async def update_node_info(self, project_id: str, node_id: str, field: str, value: str) -> Dict[str, Any]:
        """Update a specific field for a node"""
        payload = {
            'body': json.dumps({
                'project_id': project_id,
                'node_id': node_id,
                'field': field,
                'value': value
            })
        }
        
        return await self._invoke_lambda_with_retry(self.function_name, payload)

class UpdateFlowTool(BaseTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.function_name = 'risk-agent-update-flow-api'
    
    async def update_flow_info(self, project_id: str, flow_id: str, field: str, value: str) -> Dict[str, Any]:
        """Update a specific field for a flow"""
        payload = {
            'body': json.dumps({
                'project_id': project_id,
                'flow_id': flow_id,
                'field': field,
                'value': value
            })
        }
        
        return await self._invoke_lambda_with_retry(self.function_name, payload)