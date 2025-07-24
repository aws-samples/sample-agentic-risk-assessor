"""
Security Architect Agent - Handles Control Assignment
"""
import sys
sys.path.append('/app')

from agents.shared.base_agent import BaseAgent
from strands.tools import tool
from agents.shared import authenticated_a2a_client  # Enable OAuth authentication, tool
import boto3
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any
from .config import SecurityArchitectConfig
from agents.shared.logging_config import setup_optimized_logging, setup_strands_logging

# Setup optimized logging with debug level
setup_strands_logging()
logger = setup_optimized_logging(__name__, level=logging.DEBUG)

class SecurityArchitectAgent(BaseAgent):
    def __init__(self, bedrock_model=None):
        self.config = SecurityArchitectConfig().to_dict()
        
        # Create tools
        tools = [
            self._create_process_node_controls_tool(),
            self._create_get_node_details_tool(),
            self._create_get_security_assessment_tool(),
            self._create_get_latest_security_assessment_tool(),
            self._create_perform_security_assessment_tool(),
            self._create_save_security_assessment_results_tool(),
            self._create_triage_tool(),
            self._create_test_fsi_tool()
        ]
        
        # Initialize BaseAgent
        super().__init__(
            agent_name="SecurityArchitect",
            bedrock_model=bedrock_model,
            system_prompt_key="system_prompts/security_architect_system_prompt.xml",
            tools=tools
        )
        
        self.callback_handler = None

    
    def _refresh_bedrock_model(self):
        """Refresh bedrock model with new credentials"""
        from agents.security_architect.server import refresh_bedrock_session
        from strands.models import BedrockModel
        
        logger.info("Refreshing Bedrock model with new credentials...")
        new_session = refresh_bedrock_session()
        new_model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.0,
            max_tokens=16000,
            boto_session=new_session,
            timeout=300
        )
        # Update both the agent's model and the direct model reference
        self.agent.model = new_model
        logger.info("Bedrock model refreshed successfully")
    
    def _create_process_node_controls_tool(self):
        @tool
        
        def process_node_controls(project_id: str, framework: str = "nist") -> dict:
            """Process node controls assignment for a project"""
            try:
                # Get nodes from diagram analysis table (where architect saves them)
                dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
                diagram_table = dynamodb.Table('DiagramAnalysis')
                
                try:
                    response = diagram_table.get_item(Key={'project_id': project_id})
                    if 'Item' not in response:
                        return {"error": "No diagram analysis found. Please complete architecture analysis first."}
                except Exception as table_error:
                    return {"error": f"Cannot access diagram analysis: {str(table_error)}. Please complete architecture analysis first."}
                
                diagram_analysis = response['Item']
                nodes = diagram_analysis.get('nodes', [])
                
                if not nodes:
                    return {"error": "No nodes found in diagram analysis. Please complete architecture analysis first."}
                
                # Start Step Function execution
                stepfunctions = boto3.client('stepfunctions')
                state_machine_arn = f"arn:aws:states:{os.environ.get('AWS_REGION', 'us-east-1')}:{os.environ.get('AWS_ACCOUNT_ID', '')}:stateMachine:risk-agent-node-controls-mapping"
                
                execution_input = {
                    'project_id': project_id,
                    'framework': framework,
                    'nodes': nodes
                }
                
                execution_name = f"node-controls-{project_id}-{int(datetime.now().timestamp())}"
                
                response = stepfunctions.start_execution(
                    stateMachineArn=state_machine_arn,
                    name=execution_name,
                    input=json.dumps(execution_input)
                )
                
                return {
                    'message': 'Node controls processing started',
                    'execution_arn': response['executionArn'],
                    'nodes_processed': len(nodes),
                    'framework': framework
                }
                
            except Exception as e:
                return {"error": f"Control assignment failed: {str(e)}"}
        return process_node_controls
    
    def _create_get_node_details_tool(self):
        @tool
        
        def get_node_details(project_id: str, node_id: str) -> dict:
            """Get details for a specific node in a project"""
            try:
                response = self.lambda_client.invoke(
                    FunctionName='risk-agent-get_node_details',
                    Payload=json.dumps({
                        'pathParameters': {
                            'projectId': project_id,
                            'nodeId': node_id
                        }
                    })
                )
                result = json.loads(response['Payload'].read())
                return result
            except Exception as e:
                return {"error": f"Failed to get node details: {str(e)}"}
        return get_node_details
    

    

    

    
    def _create_get_security_assessment_tool(self):
        @tool
        
        def get_security_assessment(project_id: str) -> dict:
            """Get security assessment results for a project"""
            try:
                response = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_retriever',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {'id': project_id},
                        'rawPath': f'/api/projects/{project_id}/security-assessment',
                        'path': f'/api/projects/{project_id}/security-assessment'
                    })
                )
                result = json.loads(response['Payload'].read())
                if 'body' in result:
                    if isinstance(result['body'], str):
                        result = json.loads(result['body'])
                return result
            except Exception as e:
                return {"error": f"Failed to get security assessment: {str(e)}"}
        return get_security_assessment
    
    def _create_get_latest_security_assessment_tool(self):
        @tool
        
        def get_latest_security_assessment(project_id: str) -> dict:
            """Get the latest security assessment content for a project"""
            try:
                response = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_retriever',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'GET'}},
                        'pathParameters': {'id': project_id},
                        'rawPath': f'/api/projects/{project_id}/security-assessment',
                        'path': f'/api/projects/{project_id}/security-assessment'
                    })
                )
                result = json.loads(response['Payload'].read())
                if 'body' in result:
                    if isinstance(result['body'], str):
                        result = json.loads(result['body'])
                return result
            except Exception as e:
                return {"error": f"Failed to get latest security assessment: {str(e)}"}
        return get_latest_security_assessment
    
    def _create_perform_security_assessment_tool(self):
        @tool
        
        def perform_security_assessment(project_id: str) -> str:
            """Prepare security assessment prompt with architecture document content"""
            logger.error(f"🔧 TOOL CALLED: perform_security_assessment - Project: {project_id}")
            
            try:
                # Step 1: Read the FSI security review prompt template from S3
                logger.error("🔧 Step 1: Reading FSI template from S3")
                s3_client = boto3.client('s3')
                s3_key = 'system_prompts/security_architect/fsi_security_architecture_review.xml'
                bucket_name = os.getenv('APP_DATA_BUCKET')
                logger.error(f"🔧 S3 Bucket: {bucket_name}, Key: {s3_key}")
                
                response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key=s3_key
                )
                security_review_template = response['Body'].read().decode('utf-8')
                logger.error(f"🔧 FSI template loaded - Length: {len(security_review_template)} chars")
                logger.error(f"🔧 Template starts: {security_review_template[:150]}...")
                
                # Step 2: Read the architecture document
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
                
                # Get document content if available
                document_content = 'No architecture document available for this project.'
                if project_data.get('document_key'):
                    doc_response = self.lambda_client.invoke(
                        FunctionName='risk-agent-document_manager',
                        Payload=json.dumps({
                            'requestContext': {'http': {'method': 'GET'}},
                            'pathParameters': {'id': project_id},
                            'rawPath': f'/api/projects/{project_id}/document/content',
                            'path': f'/api/projects/{project_id}/document/content'
                        })
                    )
                    doc_result = json.loads(doc_response['Payload'].read())
                    if 'body' in doc_result:
                        doc_body = json.loads(doc_result['body']) if isinstance(doc_result['body'], str) else doc_result['body']
                        document_content = doc_body.get('content', 'No document content available')
                    else:
                        document_content = doc_result.get('content', 'No document content available')
                
                # Use default framework for control gap assessment
                framework = "NIST Cybersecurity Framework"  # Default framework
                document_content += f"\n\n**Compliance Framework to Use**: {framework}\n\n"
                
                # Step 3: Inject the architecture document into the prompt template
                logger.error(f"🔧 Step 3: Formatting template with document (len: {len(document_content)})")
                
                try:
                    complete_prompt = security_review_template.format(document_content=document_content)
                    logger.error(f"🔧 Format SUCCESS - Complete prompt length: {len(complete_prompt)}")
                except Exception as format_error:
                    logger.error(f"🔧 FORMAT FAILED: {format_error}")
                    logger.error(f"🔧 Format error type: {type(format_error).__name__}")
                    raise format_error
                
                # Step 4: Return the complete prompt to the agent
                logger.error(f"🔧 Step 4: Returning prompt - starts: {complete_prompt[:150]}...")
                logger.error("🔧 TOOL COMPLETED SUCCESSFULLY")
                return complete_prompt
                
            except Exception as e:
                logger.error(f"🔧 TOOL FAILED: perform_security_assessment")
                logger.error(f"🔧 Error: {str(e)}")
                logger.error(f"🔧 Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"🔧 Full traceback: {traceback.format_exc()}")
                error_msg = f"Error preparing security assessment prompt: {str(e)}"
                logger.error(f"🔧 Returning error: {error_msg}")
                return error_msg
        return perform_security_assessment
    
    def _create_save_security_assessment_results_tool(self):
        @tool
        
        def save_security_assessment_results(project_id: str, assessment_content: str = "", version_type: str = "manual") -> dict:
            """Save security assessment content to storage with timestamp"""
            import time
            from datetime import datetime
            start_time = time.time()
            
            if not project_id:
                return {
                    "status": "error",
                    "message": "Project ID is required for saving."
                }
            
            # If no content provided, extract from conversation history (backward compatibility)
            if not assessment_content:
                for message in reversed(self.agent.messages):
                    if message.get("role") == "assistant":
                        for content in message.get("content", []):
                            if isinstance(content, dict) and "text" in content:
                                text = content["text"]
                                # Expanded keywords for triage assessments
                                if ("Security Assessment" in text or "Security Review" in text or "FSI Security" in text or 
                                    "Control Assessment Results" in text or "Framework Used" in text or "Executive Summary" in text or
                                    "| Control ID |" in text or "Effectiveness" in text or "Triage Assessment" in text or
                                    "Security Triage" in text or "Risk Assessment" in text or "Compliance" in text or
                                    "Implementation Status" in text or "Gap Analysis" in text) and len(text) > 200:
                                    assessment_content = text
                                    break
                            elif isinstance(content, str) and ("Security Assessment" in content or "Security Review" in content or "FSI Security" in content or
                                                               "Control Assessment Results" in content or "Framework Used" in content or "Executive Summary" in content or
                                                               "| Control ID |" in content or "Effectiveness" in content or "Triage Assessment" in content or
                                                               "Security Triage" in content or "Risk Assessment" in content or "Compliance" in content or
                                                               "Implementation Status" in content or "Gap Analysis" in content) and len(content) > 200:
                                assessment_content = content
                                break
                        if assessment_content:
                            break
            
            if not assessment_content:
                return {
                    "status": "error",
                    "message": "No security assessment content provided or found in conversation history."
                }
            
            logger.info(f"TOOL CALLED: save_security_assessment_results - Project: {project_id}")
            
            try:
                # Add timestamp to assessment content
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                timestamped_content = f"# Security Assessment Report\n\n**Generated on:** {current_time}\n\n{assessment_content}"
                
                save_result = self.lambda_client.invoke(
                    FunctionName='risk-agent-assessment_saver',
                    Payload=json.dumps({
                        'requestContext': {'http': {'method': 'POST'}},
                        'pathParameters': {'id': project_id},
                        'body': json.dumps({
                            'assessment_type': 'security-assessments',
                            'assessment_content': timestamped_content,
                            'version_type': version_type
                        })
                    })
                )
                
                # Parse Lambda response
                response_payload = json.loads(save_result['Payload'].read())
                if save_result['StatusCode'] != 200 or response_payload.get('statusCode') != 200:
                    body = response_payload.get('body', '{}')
                    if isinstance(body, str):
                        try:
                            body = json.loads(body)
                        except:
                            body = {}
                    error_msg = body.get('error', 'Unknown error')
                    return {
                        "status": "error",
                        "message": f"Save failed: {error_msg}"
                    }
                
                logger.info(f"Security assessment saved successfully in {time.time() - start_time:.2f}s")
                
                return {
                    "status": "success",
                    "message": "Security assessment saved successfully with timestamp. REFRESH_SECURITY_ASSESSMENT"
                }
                
            except Exception as e:
                logger.error(f"Failed to save security assessment: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Error saving assessment: {str(e)}"
                }
        return save_security_assessment_results
    
    def _create_triage_tool(self):
        @tool
        
        def triage(project_id: str) -> str:
            """Get security triage assessment prompt from S3 for intelligent security assessment enhancement"""
            try:
                from .tools.triage import TriageTool
                triage_tool = TriageTool()
                prompt = triage_tool.get_triage_prompt()
                return f"Security triage prompt loaded for project {project_id}:\n\n{prompt}"
            except Exception as e:
                return f"Error loading security triage prompt: {str(e)}"
        return triage
    
    def _create_test_fsi_tool(self):
        @tool
        
        def test_fsi_read() -> str:
            """Test tool that only reads and returns the FSI prompt from S3"""
            logger.error("🔧 TEST TOOL: test_fsi_read called")
            try:
                s3_client = boto3.client('s3')
                s3_key = 'system_prompts/security_architect/fsi_security_architecture_review.md'
                bucket_name = os.getenv('APP_DATA_BUCKET')
                logger.error(f"🔧 Reading S3: {bucket_name}/{s3_key}")
                
                response = s3_client.get_object(
                    Bucket=os.getenv('APP_DATA_BUCKET'),
                    Key=s3_key
                )
                fsi_content = response['Body'].read().decode('utf-8')
                logger.error(f"🔧 FSI content length: {len(fsi_content)}")
                logger.error(f"🔧 FSI content: {fsi_content}")
                
                return fsi_content
            except Exception as e:
                logger.error(f"🔧 TEST TOOL FAILED: {str(e)}")
                return f"Error reading FSI prompt: {str(e)}"
        return test_fsi_read
    
    def _create_perform_fsi_security_assessment_tool(self):
        @tool
        
        def perform_fsi_security_assessment(project_id: str) -> dict:
            """Loads and returns the FSI Security Assessment prompt for a given project"""
            try:
                # Read the security assessment prompt
                prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'security_assessment.txt')
                
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                
                # Format the prompt with project_id
                formatted_prompt = prompt_content.format(project_id=project_id)
                
                return {
                    "success": True,
                    "prompt": formatted_prompt,
                    "project_id": project_id,
                    "message": f"FSI Security Assessment prompt loaded for project {project_id}"
                }
                
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "Security assessment prompt file not found",
                    "project_id": project_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error loading security assessment prompt: {str(e)}",
                    "project_id": project_id
                }
        return perform_fsi_security_assessment
    

    
    def _extract_project_id(self, message: str) -> str:
        """Extract project ID from message"""
        if 'Project:' in message:
            parts = message.split('Project:', 1)[1].split(' - ', 1)
            return parts[0].strip()
        elif message.startswith('start_security_assessment'):
            parts = message.split(' ', 1)
            return parts[1].strip() if len(parts) > 1 else None
        elif message.startswith('generate_security_questions'):
            parts = message.split(' ', 1)
            return parts[1].strip() if len(parts) > 1 else None
        return None
    

    
    def set_progress_tracker(self, websocket):
        """Set WebSocket for progress tracking using Strands callback handler"""
        from agents.shared.progress_callback_handler import ProgressCallbackHandler
        from agents.shared.progress_hook_provider import ProgressHookProvider
        
        # Create progress callback handler
        self.callback_handler = ProgressCallbackHandler(websocket, "security-architect")
        self.agent.callback_handler = self.callback_handler
        
        # Optional: Add detailed hook provider for lifecycle events
        hook_provider = ProgressHookProvider(websocket, "security-architect")
        if hasattr(self.agent, '_hook_registry') and self.agent._hook_registry:
            self.agent._hook_registry.add_hook(hook_provider)
        
        logger.info("Progress tracking enabled for Security Architect Agent")
    def _get_node_controls_data(self, project_id: str) -> list:
        """Get control assignments from NodeControls table"""
        try:
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('NodeControls')
            
            response = table.scan(
                FilterExpression='project_id = :pid',
                ExpressionAttributeValues={':pid': project_id}
            )
            
            control_mapping = []
            for item in response.get('Items', []):
                # Extract controls from mapped_controls field
                mapped_controls = item.get('mapped_controls', [])
                for control in mapped_controls:
                    control_mapping.append({
                        'control_id': control.get('control_id', ''),
                        'control_name': control.get('control_name', ''),
                        'implementation_status': 'Partially Implemented',  # Default status
                        'evidence': f"Mapped to {item.get('node_name', 'node')} ({item.get('node_type', 'unknown')})",
                        'gaps': [],
                        'recommendations': [control.get('rationale', 'Review implementation')]
                    })
            
            return control_mapping
        except Exception as e:
            logger.error(f"Error getting node controls: {str(e)}")
            return []
    
    def _perform_control_gap_assessment_direct(self, project_id: str) -> str:
        """Perform direct control gap assessment and return formatted response"""
        try:
            # Get the complete prompt from the tool
            complete_prompt = self._create_perform_control_gap_assessment_tool()(project_id)
            
            if complete_prompt.startswith("Error"):
                return f"❌ Control gap assessment failed: {complete_prompt}"
            
            # Return the complete prompt for the agent to process
            return complete_prompt
            
        except Exception as e:
            return f"❌ Error performing control gap assessment: {str(e)}"
