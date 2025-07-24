"""
Architect Agent - Native Strands Tools
"""
import sys
import os
import json
import boto3
sys.path.append('/app')

from agents.shared.base_agent import BaseAgent
from strands.tools import tool

class ArchitectAgent(BaseAgent):
    def __init__(self, bedrock_model=None):
        # Create native Strands tools
        tools = [
            self._create_get_project_tool(),
            self._create_get_diagram_analysis_tool(),
            self._create_get_node_details_tool(),
            self._create_get_node_controls_tool(),
            self._create_update_node_info_tool(),
            self._create_update_flow_info_tool(),
            self._create_save_architecture_review_tool(),
            self._create_analyze_diagram_tool(),
            self._create_get_latest_architecture_review_tool(),
            self._create_get_fsi_review_prompt_tool()
        ]
        
        # Initialize without YAML configuration
        super().__init__(
            agent_name="Architect",
            bedrock_model=bedrock_model,
            system_prompt_key="system_prompts/architect_system_prompt.xml",
            tools=tools
        )
    
    def _create_get_project_tool(self):
        @tool
        
        def get_project(project_id: str) -> dict:
            """Get project details by project ID"""
            return self._invoke_lambda('risk-agent-projects', {
                'requestContext': {'http': {'method': 'GET'}},
                'pathParameters': {'id': project_id}
            })
        return get_project
    
    def _create_get_diagram_analysis_tool(self):
        @tool
        
        def get_diagram_analysis(project_id: str) -> dict:
            """Get diagram analysis for a project, including all nodes and flows"""
            return self._invoke_lambda('risk-agent-diagram_analysis', {
                'requestContext': {'http': {'method': 'GET'}},
                'pathParameters': {'id': project_id}
            })
        return get_diagram_analysis
    
    def _create_get_node_details_tool(self):
        @tool
        
        def get_node_details(project_id: str, node_id: str) -> dict:
            """Get details for a specific node in a project"""
            return self._invoke_lambda('risk-agent-get_node_details', {
                'pathParameters': {'projectId': project_id, 'nodeId': node_id}
            })
        return get_node_details
    
    def _create_get_node_controls_tool(self):
        @tool
        
        def get_node_controls(project_id: str) -> dict:
            """Get all nodes with controls for a project"""
            return self._invoke_lambda('risk-agent-get_node_controls', {
                'pathParameters': {'id': project_id}
            })
        return get_node_controls
    
    def _create_update_node_info_tool(self):
        @tool
        
        def update_node_info(project_id: str, node_id: str, field: str, value: str) -> dict:
            """Update a specific field for a node (e.g., name, type, description)"""
            return self._invoke_lambda('risk-agent-update_node', {
                'body': json.dumps({
                    'project_id': project_id,
                    'node_id': node_id,
                    'field': field,
                    'value': value
                })
            })
        return update_node_info
    
    def _create_update_flow_info_tool(self):
        @tool
        
        def update_flow_info(project_id: str, flow_id: str, field: str, value: str) -> dict:
            """Update a specific field for a flow (e.g., type, description, protocol)"""
            return self._invoke_lambda('risk-agent-update_flow', {
                'body': json.dumps({
                    'project_id': project_id,
                    'flow_id': flow_id,
                    'field': field,
                    'value': value
                })
            })
        return update_flow_info
    
    def _create_save_architecture_review_tool(self):
        @tool
        
        def save_architecture_review(project_id: str, review_content: str, version_type: str = "manual") -> dict:
            """Save architecture review content for a project"""
            return self._invoke_lambda('risk-agent-assessment_saver', {
                'requestContext': {'http': {'method': 'POST'}},
                'pathParameters': {'id': project_id},
                'body': json.dumps({
                    'assessment_type': 'architecture-reviews',
                    'assessment_content': review_content,
                    'version_type': version_type
                })
            })
        return save_architecture_review
    
    def _create_analyze_diagram_tool(self):
        @tool
        
        def analyze_diagram(project_id: str) -> dict:
            """Analyze architecture diagram to extract nodes and flows"""
            return self._invoke_lambda('risk-agent-diagram_analysis', {
                'requestContext': {'http': {'method': 'POST'}},
                'pathParameters': {'id': project_id}
            })
        return analyze_diagram
    
    def _create_get_latest_architecture_review_tool(self):
        @tool
        
        def get_latest_architecture_review(project_id: str) -> dict:
            """Get the latest architecture review content for a project"""
            try:
                # Get list of reviews
                reviews_response = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_retriever',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {'id': project_id},
                        'rawPath': f'/api/projects/{project_id}/architecture-review',
                        'path': f'/api/projects/{project_id}/architecture-review',
                        'queryStringParameters': {'type': 'architecture-reviews'}
                    })
                )
                reviews_result = json.loads(reviews_response['Payload'].read())
                if 'body' in reviews_result:
                    if isinstance(reviews_result['body'], str):
                        reviews_data = json.loads(reviews_result['body'])
                    else:
                        reviews_data = reviews_result['body']
                else:
                    reviews_data = reviews_result
                
                if not reviews_data.get('reviews') or len(reviews_data['reviews']) == 0:
                    return {"error": "No architecture reviews found for this project"}
                
                # Get the latest review (first in list)
                latest_review = reviews_data['reviews'][0]
                
                # Get the review content
                content_response = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_content',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {
                            'id': project_id,
                            'assessment_id': latest_review['review_id']
                        },
                        'rawPath': f'/api/projects/{project_id}/architecture-review/{latest_review["review_id"]}',
                        'path': f'/api/projects/{project_id}/architecture-review/{latest_review["review_id"]}',
                        'queryStringParameters': {'type': 'architecture-reviews'}
                    })
                )
                content_result = json.loads(content_response['Payload'].read())
                if 'body' in content_result:
                    if isinstance(content_result['body'], str):
                        content_data = json.loads(content_result['body'])
                    else:
                        content_data = content_result['body']
                else:
                    content_data = content_result
                
                return {
                    "review_id": latest_review['review_id'],
                    "version": latest_review.get('version', 'unknown'),
                    "timestamp": latest_review.get('timestamp', 'unknown'),
                    "content": content_data.get('content', '')
                }
                
            except Exception as e:
                return {"error": f"Failed to get latest architecture review: {str(e)}"}
        return get_latest_architecture_review
    
    def _create_get_fsi_review_prompt_tool(self):
        from strands.tools import tool
        import boto3
        import json
        
        @tool
        
        def get_fsi_review_prompt(project_id: str) -> dict:
            """Get FSI architecture review prompt with project document content"""
            try:
                # Get project document content
                project_response = self.lambda_client.invoke(
                    FunctionName='risk-agent-projects',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {'id': project_id}
                    })
                )
                project_result = json.loads(project_response['Payload'].read())
                if 'body' in project_result:
                    project_data = json.loads(project_result['body']) if isinstance(project_result['body'], str) else project_result['body']
                else:
                    project_data = project_result
                
                document_content = 'No document available'
                if project_data.get('document_key'):
                    doc_response = self.lambda_client.invoke(
                        FunctionName='risk-agent-document_manager',
                        Payload=json.dumps({
                            'requestContext': {'http': {'method': 'GET'}},
                            'pathParameters': {'id': project_id},
                            'queryStringParameters': {'action': 'get_content'}
                        })
                    )
                    doc_result = json.loads(doc_response['Payload'].read())
                    if 'body' in doc_result:
                        doc_body = json.loads(doc_result['body']) if isinstance(doc_result['body'], str) else doc_result['body']
                        document_content = doc_body.get('content', 'No document content available')
                    else:
                        document_content = doc_result.get('content', 'No document content available')
                
                # Load FSI review prompt template from S3
                s3_client = boto3.client('s3')
                response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key='system_prompts/architect/fsi_architecture_review.xml'
                )
                fsi_review_template = response['Body'].read().decode('utf-8')
                
                # Format prompt with document content
                formatted_prompt = fsi_review_template.format(document_content=document_content)
                
                return {
                    "status": "success",
                    "prompt": formatted_prompt,
                    "project_id": project_id
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to get FSI review prompt: {str(e)}"
                }
        return get_fsi_review_prompt
    
