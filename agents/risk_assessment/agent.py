"""
Risk Assessment Agent - Handles Risk Analysis
"""
import sys
sys.path.append('/app')

from agents.shared.base_agent import BaseAgent
from strands.tools import tool
from agents.shared import authenticated_a2a_client  # Enable OAuth authentication, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands_tools.a2a_client import A2AClientToolProvider
import boto3
import json
import os
import logging
from .config import RiskAssessmentConfig
from agents.shared.logging_config import setup_optimized_logging, setup_strands_logging

# Setup optimized logging with info level
setup_strands_logging()
logger = setup_optimized_logging(__name__, level=logging.INFO)

class RiskAssessmentAgent(BaseAgent):
    def __init__(self, bedrock_model=None):
        self.config = RiskAssessmentConfig().to_dict()
        
        # Create tools
        full_tool, quick_tool, demo_tool = self._create_full_risk_assessment_tool()
        tools = [
            full_tool,
            quick_tool,
            demo_tool,
            self._create_save_risk_assessment_tool(),
            self._create_retrieve_risk_assessment_tool()
        ]
        
        # Initialize BaseAgent
        super().__init__(
            agent_name="RiskAssessment",
            bedrock_model=bedrock_model,
            system_prompt_key="system_prompts/risk_assessment_system_prompt.xml",
            tools=tools
        )
    
    def _refresh_bedrock_model(self):
        """Refresh bedrock model with new credentials"""
        from agents.risk_assessment.server import refresh_bedrock_session
        from strands.models import BedrockModel
        
        new_model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.0,
            max_tokens=40000,
            boto_session=refresh_bedrock_session()
        )
        self.agent.model = new_model
    

    

    

    
    def _create_full_risk_assessment_tool(self):
        @tool
        
        def perform_full_risk_assessment(project_id: str, framework: str = "FSI", is_quick: bool = False) -> dict:
            """Perform comprehensive FSI risk assessment using A2A communication and templates"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: perform_full_risk_assessment - Project: {project_id}, Framework: {framework}")
            try:
                # Load appropriate template based on is_quick parameter
                s3_client = boto3.client('s3')
                template_key = 'risk_assessment/templates/FSI_Risk_Assessment_Template_Short.md' if is_quick else 'risk_assessment/templates/FSI_Risk_Framework_Template.md'
                prompt_key = 'risk_assessment/prompts/fsi_assessment_prompt_short.md' if is_quick else 'risk_assessment/prompts/fsi_assessment_prompt.xml'
                
                template_response = s3_client.get_object(Bucket=os.getenv('APP_DATA_BUCKET'), Key=template_key)
                fsi_template = template_response['Body'].read().decode('utf-8')
                
                prompts_response = s3_client.get_object(Bucket=os.getenv('APP_DATA_BUCKET'), Key=prompt_key)
                fsi_prompt_template = prompts_response['Body'].read().decode('utf-8')
                
                # Create assessment prompt
                assessment_prompt = fsi_prompt_template.format(project_id=project_id, fsi_template=fsi_template)
                
                logger.info(f"Assessment prompt prepared in {time.time() - start_time:.2f}s")
                return {
                    "status": "success",
                    "content": [
                        {"text": f"Please process this FSI risk assessment for project {project_id}:\n\n{assessment_prompt}"}
                    ]
                }
                
            except Exception as e:
                logger.error(f"Risk assessment failed after {time.time() - start_time:.2f}s: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Risk assessment failed: {str(e)}"}]
                }
        @tool
        
        def perform_quick_risk_assessment(project_id: str, framework: str = "FSI") -> dict:
            """Perform quick FSI risk assessment using condensed template"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: perform_quick_risk_assessment - Project: {project_id}, Framework: {framework}")
            try:
                # Load FSI short template from S3
                s3_client = boto3.client('s3')
                template_response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key='risk_assessment/templates/FSI_Risk_Assessment_Template_Short.md'
                )
                fsi_template = template_response['Body'].read().decode('utf-8')
                
                # Load FSI short assessment prompt from S3 (XML format)
                prompts_response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key='risk_assessment/prompts/fsi_assessment_prompt_short.xml'
                )
                fsi_prompt_template = prompts_response['Body'].read().decode('utf-8')
                
                # Create assessment prompt
                assessment_prompt = fsi_prompt_template.format(project_id=project_id, fsi_template=fsi_template)
                
                logger.info(f"Quick assessment prompt prepared in {time.time() - start_time:.2f}s")
                return {
                    "status": "success",
                    "content": [
                        {"text": f"Please process this quick FSI risk assessment for project {project_id}:\n\n{assessment_prompt}"}
                    ]
                }
                
            except Exception as e:
                logger.error(f"Quick risk assessment failed after {time.time() - start_time:.2f}s: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Quick risk assessment failed: {str(e)}"}]
                }
        
        @tool
        
        def perform_demo_risk_assessment(project_id: str, framework: str = "FSI") -> dict:
            """Perform demo FSI risk assessment with token limits for fast completion (~1 minute)"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: perform_demo_risk_assessment - Project: {project_id}, Framework: {framework}")
            try:
                # Load FSI demo template from S3
                s3_client = boto3.client('s3')
                template_response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key='risk_assessment/templates/FSI_Risk_Assessment_Template_Demo.md'
                )
                fsi_demo_template = template_response['Body'].read().decode('utf-8')
                
                # Load FSI demo assessment prompt from S3 (XML format)
                prompts_response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key='risk_assessment/prompts/fsi_assessment_prompt_demo.xml'
                )
                fsi_demo_prompt_template = prompts_response['Body'].read().decode('utf-8')
                
                # Create demo assessment prompt
                demo_assessment_prompt = fsi_demo_prompt_template.format(
                    project_id=project_id, 
                    fsi_demo_template=fsi_demo_template
                )
                
                logger.info(f"Demo assessment prompt prepared in {time.time() - start_time:.2f}s")
                return {
                    "status": "success",
                    "content": [
                        {"text": f"Please process this DEMO FSI risk assessment for project {project_id}:\n\n{demo_assessment_prompt}"}
                    ]
                }
                
            except Exception as e:
                logger.error(f"Demo risk assessment failed after {time.time() - start_time:.2f}s: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Demo risk assessment failed: {str(e)}"}]
                }
        
        return perform_full_risk_assessment, perform_quick_risk_assessment, perform_demo_risk_assessment
    
    def _create_save_risk_assessment_tool(self):
        @tool
        
        def save_risk_assessment(project_id: str = "") -> dict:
            """Save completed FSI risk assessment to storage"""
            import time
            from datetime import datetime
            start_time = time.time()
            
            if not project_id:
                return {
                    "status": "error",
                    "content": [{"text": "Project ID is required for saving."}]
                }
            
            # Extract assessment content from conversation history
            assessment_content = ""
            for message in reversed(self.agent.messages):
                if message.get("role") == "assistant":
                    for content in message.get("content", []):
                        if isinstance(content, dict) and "text" in content:
                            text = content["text"]
                            if "Risk Assessment" in text and len(text) > 500:
                                assessment_content = text
                                break
                        elif isinstance(content, str) and "Risk Assessment" in content and len(content) > 500:
                            assessment_content = content
                            break
                    if assessment_content:
                        break
            
            if not assessment_content:
                return {
                    "status": "error",
                    "content": [{"text": "No risk assessment found in conversation history to save."}]
                }
            
            logger.info(f"TOOL CALLED: save_risk_assessment - Project: {project_id}")
            
            try:
                # Add timestamp to assessment content
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                timestamped_content = f"# Risk Assessment Report\n\n**Generated on:** {current_time}\n\n{assessment_content}"
                
                save_result = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_saver',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'POST'}},
                        'pathParameters': {'id': project_id},
                        'body': json.dumps({
                            'assessment_type': 'risk-assessments',
                            'assessment_content': timestamped_content
                        })
                    })
                )
                
                # Parse Lambda response
                response_payload = json.loads(save_result['Payload'].read())
                if save_result['StatusCode'] != 200 or response_payload.get('statusCode') != 200:
                    error_msg = response_payload.get('body', {}).get('error', 'Unknown error')
                    return {
                        "status": "error",
                        "content": [{"text": f"Save failed: {error_msg}"}]
                    }
                
                logger.info(f"Assessment saved successfully in {time.time() - start_time:.2f}s")
                
                return {
                    "status": "success",
                    "content": [
                        {"text": "FSI risk assessment saved successfully with timestamp. REFRESH_RISK_ASSESSMENT"},
                        {"json": {"project_id": project_id}}
                    ]
                }
                
            except Exception as e:
                logger.error(f"Failed to save risk assessment: {str(e)}")
                return {
                    "status": "error",
                    "content": [
                        {"text": f"Error saving assessment: {str(e)}"},
                        {"json": {"project_id": project_id if project_id else "unknown"}}
                    ]
                }
        return save_risk_assessment
    
    def _create_retrieve_risk_assessment_tool(self):
        @tool
        
        def retrieve_risk_assessment(project_id: str) -> dict:
            """Retrieve the latest risk assessment from S3 for a project"""
            import time
            start_time = time.time()
            logger.info(f"TOOL CALLED: retrieve_risk_assessment - Project: {project_id}")
            
            if not project_id:
                return {
                    "status": "error",
                    "content": [{"text": "Project ID is required for retrieval."}]
                }
            
            try:
                retrieve_result = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_content',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {'id': project_id, 'assessment_id': 'latest'},
                        'rawPath': f'/api/projects/{project_id}/risk-assessment/latest',
                        'path': f'/api/projects/{project_id}/risk-assessment/latest',
                        'queryStringParameters': {'type': 'risk-assessments'}
                    })
                )
                
                # Parse Lambda response
                response_payload = json.loads(retrieve_result['Payload'].read())
                
                if retrieve_result['StatusCode'] != 200:
                    return {
                        "status": "error",
                        "content": [{"text": f"Lambda invocation failed with status {retrieve_result['StatusCode']}"}]
                    }
                
                if response_payload.get('statusCode') != 200:
                    error_msg = response_payload.get('body', 'Risk assessment not found')
                    logger.info(f"Lambda returned non-200 status: {response_payload.get('statusCode')}, body: {error_msg}")
                    return {
                        "status": "error", 
                        "content": [{"text": f"No risk assessment found for project {project_id}. Lambda response: {error_msg}"}]
                    }
                
                # Extract assessment content from response
                body = response_payload.get('body', '{}')
                if isinstance(body, str):
                    body = json.loads(body)
                
                assessment_content = body.get('content', '')  # Lambda returns 'content', not 'assessment_content'
                
                if not assessment_content:
                    return {
                        "status": "error",
                        "content": [{"text": f"No assessment content found for project {project_id}"}]
                    }
                
                logger.info(f"Risk assessment retrieved successfully in {time.time() - start_time:.2f}s")
                
                return {
                    "status": "success",
                    "content": [
                        {"text": f"Latest risk assessment for project {project_id}:\n\n{assessment_content}"}
                    ]
                }
                
            except Exception as e:
                logger.error(f"Failed to retrieve risk assessment: {str(e)}")
                return {
                    "status": "error",
                    "content": [{"text": f"Error retrieving assessment: {str(e)}"}]
                }
        return retrieve_risk_assessment
    
