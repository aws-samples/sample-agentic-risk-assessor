import json
import os
import boto3
import logging
import time
import traceback
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

# Third-party imports
import instructor
from pydantic import BaseModel, Field, computed_field

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Pydantic models for structured output
class SecurityControl(BaseModel):
    """Represents a security control for a service with comprehensive analysis"""
    id: str = Field(description="Control ID (e.g., 'AC-1', 'SC-7')")
    category: str = Field(description="Control category/family (e.g., 'Access Control', 'System and Communications Protection')")
    priority: str = Field(description="Priority level (High, Medium, Low)")
    description: str = Field(description="Description of how the control applies to this service")
    name: Optional[str] = Field(default="", description="Control name or title")
    reason: Optional[str] = Field(default="", description="Reason why control is not applicable (for non-applicable controls only)")
    
    # Control Mapping Details
    requirement: Optional[str] = Field(default="", description="Specific control requirement")
    capabilities: Optional[str] = Field(default="", description="Specific service capabilities that address this control")
    implementation_approach: Optional[str] = Field(default="", description="Recommended implementation approach")
    
    # Verification Criteria
    automated_checks: Optional[str] = Field(default="", description="Automated validation methods")
    measurable_thresholds: Optional[str] = Field(default="", description="Quantifiable success criteria")
    audit_evidence: Optional[str] = Field(default="", description="Required audit documentation")
    
    # Risk Assessment
    criticality_score: Optional[int] = Field(default=5, description="Risk criticality (1-10 scale)")
    complexity: Optional[str] = Field(default="Medium", description="Implementation complexity (Low/Medium/High)")
    cost_category: Optional[str] = Field(default="Medium", description="Implementation cost (Low/Medium/High)")
    
    # Implementation Levels
    basic_level: Optional[str] = Field(default="", description="Basic implementation approach")
    managed_level: Optional[str] = Field(default="", description="Managed implementation approach")
    optimized_level: Optional[str] = Field(default="", description="Optimized implementation approach")
    predictive_level: Optional[str] = Field(default="", description="Predictive implementation approach")
    
    # Dependencies
    prerequisites: Optional[str] = Field(default="", description="Required prerequisites")
    enablers: Optional[str] = Field(default="", description="Supporting technologies/services")
    conflicts: Optional[str] = Field(default="", description="Potential conflicts or limitations")
    
    # Validation Methods
    cli_commands: Optional[str] = Field(default="", description="CLI validation commands")
    monitoring_setup: Optional[str] = Field(default="", description="Monitoring configuration")
    validation_procedures: Optional[str] = Field(default="", description="Step-by-step validation process")

class ServiceControlsMapping(BaseModel):
    """Complete mapping of security controls for a service"""
    applicable_controls: List[SecurityControl] = Field(description="Controls that apply to this service")
    non_applicable_controls: List[SecurityControl] = Field(description="Controls that do not apply to this service")
    
    @computed_field
    @property
    def total_controls_count(self) -> int:
        """Returns the total number of controls (applicable + non-applicable)"""
        return len(self.applicable_controls) + len(self.non_applicable_controls)
    
    @computed_field
    @property
    def applicable_count(self) -> int:
        """Returns the number of applicable controls"""
        return len(self.applicable_controls)

# Configuration from environment
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'V7XKVYPJFR')
RAG_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')  # Use BEDROCK_MODEL_ID from terraform
BEDROCK_ACCOUNT_ID = os.environ.get('BEDROCK_ACCOUNT_ID')
BEDROCK_ROLE_NAME = os.environ.get('BEDROCK_ROLE_NAME', 'risk-agent-bedrock-role')

def get_model_arn():
    """Get appropriate model ARN based on account configuration"""
    try:
        # If RAG_MODEL_ID is already a full ARN, use it directly
        if RAG_MODEL_ID.startswith('arn:aws:bedrock:'):
            logger.info(f"Using provided ARN: {RAG_MODEL_ID}")
            return RAG_MODEL_ID
        
        # Get current account
        sts = boto3.client('sts')
        current_account = sts.get_caller_identity()['Account']
        
        # Check if cross-account access is needed
        if BEDROCK_ACCOUNT_ID and current_account != BEDROCK_ACCOUNT_ID:
            # Cross account - use inference profile ARN
            model_arn = f'arn:aws:bedrock:us-east-1:{BEDROCK_ACCOUNT_ID}:inference-profile/{RAG_MODEL_ID}'
            logger.info(f"Using cross-account inference profile ARN: {model_arn}")
            return model_arn
        else:
            # Same account - use inference profile ARN for regional models, foundation model for others
            if RAG_MODEL_ID.startswith(('us.', 'eu.', 'global.', 'ap.')):
                model_arn = f'arn:aws:bedrock:us-east-1:{current_account}:inference-profile/{RAG_MODEL_ID}'
                logger.info(f"Using inference profile ARN: {model_arn}")
            else:
                model_arn = f'arn:aws:bedrock:us-east-1::foundation-model/{RAG_MODEL_ID}'
                logger.info(f"Using foundation model ARN: {model_arn}")
            return model_arn
            
    except Exception as e:
        logger.error(f"Error determining model ARN: {str(e)}")
        # Fallback to using RAG_MODEL_ID as-is
        return RAG_MODEL_ID
        return f'arn:aws:bedrock:us-east-1::foundation-model/{RAG_MODEL_ID}'

def get_bedrock_runtime_client():
    """Get Bedrock Runtime client with same account detection logic as diagram analysis"""
    try:
        # Get current account
        sts = boto3.client('sts')
        current_account = sts.get_caller_identity()['Account']
        
        # Check if cross-account access is needed
        if BEDROCK_ACCOUNT_ID and current_account != BEDROCK_ACCOUNT_ID:
            # Cross account - assume role
            logger.info(f"Cross account ({current_account} -> {BEDROCK_ACCOUNT_ID}) - assuming role")
            bedrock_role_arn = f"arn:aws:iam::{BEDROCK_ACCOUNT_ID}:role/{BEDROCK_ROLE_NAME}"
            
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=bedrock_role_arn,
                RoleSessionName='bedrock-rag-session'
            )
            
            credentials = assumed_role['Credentials']
            return boto3.client(
                'bedrock-runtime',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            # Same account - use direct credentials
            logger.info(f"Same account ({current_account}) - using direct credentials")
            return boto3.client('bedrock-runtime')
            
    except Exception as e:
        logger.error(f"Error setting up Bedrock Runtime client: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def get_bedrock_agent_runtime_client():
    """Get Bedrock Agent Runtime client for RAG queries"""
    try:
        # Get current account
        sts = boto3.client('sts')
        current_account = sts.get_caller_identity()['Account']
        
        # Check if cross-account access is needed
        if BEDROCK_ACCOUNT_ID and current_account != BEDROCK_ACCOUNT_ID:
            # Cross account - assume role
            logger.info(f"Cross account ({current_account} -> {BEDROCK_ACCOUNT_ID}) - assuming role")
            bedrock_role_arn = f"arn:aws:iam::{BEDROCK_ACCOUNT_ID}:role/{BEDROCK_ROLE_NAME}"
            
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=bedrock_role_arn,
                RoleSessionName='bedrock-rag-session'
            )
            
            credentials = assumed_role['Credentials']
            return boto3.client(
                'bedrock-agent-runtime',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
        else:
            # Same account - use direct credentials
            logger.info(f"Same account ({current_account}) - using direct credentials")
            return boto3.client('bedrock-agent-runtime')
            
    except Exception as e:
        logger.error(f"Error setting up Bedrock Agent Runtime client: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def get_instructor_client():
    """Initialize Instructor client from Bedrock Runtime client like diagram analysis"""
    bedrock_runtime = get_bedrock_runtime_client()
    if not bedrock_runtime:
        logger.warning("Cannot initialize Instructor client: Bedrock Runtime client is not available")
        return None
    
    try:
        instructor_client = instructor.from_bedrock(client=bedrock_runtime)
        logger.info("Instructor client initialized successfully")
        return instructor_client
    except Exception as e:
        logger.error(f"Error initializing Instructor client: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def retry_retrieve_and_generate(bedrock_client, input_text, model_arn, max_retries=6):
    """Retry RetrieveAndGenerate with exponential backoff for throttling"""
    for attempt in range(max_retries):
        try:
            response = bedrock_client.retrieve_and_generate(
                input={'text': input_text},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                        'modelArn': model_arn
                    }
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                    logger.warning(f"Throttling detected, retry {attempt + 1}/{max_retries} after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries ({max_retries}) exceeded for throttling")
                    raise
            else:
                raise

def lambda_handler(event, context):
    """RAG query handler with structured output using Instructor"""
    try:
        logger.info(f"Event received: {json.dumps(event)}")
        
        # Extract service name and prompt from event
        service_name = event.get('service')
        prompt = event.get('prompt')
        
        if not service_name:
            logger.error("Service name is required")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Service name is required'})
            }
            
        if not prompt:
            logger.error("Prompt is required")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Prompt is required'})
            }
        
        logger.info(f"Processing structured controls mapping for service: {service_name}")
        return structured_controls_mapping(service_name, prompt)
            
    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def structured_controls_mapping(service_name, prompt):
    """Generate structured controls mapping using Instructor like diagram analysis"""
    try:
        logger.info(f"Starting structured controls mapping for service: {service_name}")
        
        # Validate inputs
        if not service_name or not service_name.strip():
            logger.error("Service name is empty or invalid")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'applicable_controls': [],
                    'non_applicable_controls': [],
                    'error': 'Service name is required'
                })
            }
        
        if not prompt or not prompt.strip():
            logger.error("Prompt is empty or invalid")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'applicable_controls': [],
                    'non_applicable_controls': [],
                    'error': 'Prompt is required'
                })
            }
        
        # Get Instructor client
        instructor_client = get_instructor_client()
        if not instructor_client:
            raise Exception("Instructor client not initialized")
        
        # Create structured prompt for controls mapping
        # Create structured prompt for controls mapping with comprehensive analysis
        structured_prompt = f"""
{prompt}

CRITICAL: You MUST provide ALL of the following fields for each applicable control. Do not omit any fields:

REQUIRED FIELDS FOR EACH APPLICABLE CONTROL:
- id: Control identifier (e.g., 'AC-1', 'SC-7')
- category: Control family/category
- priority: High/Medium/Low priority
- description: How the control applies to {service_name}
- name: Control name/title
- requirement: Specific control requirement text
- capabilities: Specific {service_name} capabilities that address this control
- implementation_approach: Recommended implementation approach
- automated_checks: Automated validation methods and tools
- measurable_thresholds: Quantifiable success criteria and metrics
- audit_evidence: Required audit documentation and evidence
- criticality_score: Risk criticality on 1-10 scale (10 = highest risk)
- complexity: Implementation complexity (Low/Medium/High)
- cost_category: Implementation cost category (Low/Medium/High)
- basic_level: Basic implementation approach
- managed_level: Managed implementation approach
- optimized_level: Optimized implementation approach
- predictive_level: Predictive implementation approach
- prerequisites: Required prerequisites and dependencies
- enablers: Supporting technologies, services, or configurations
- conflicts: Potential conflicts, limitations, or incompatibilities
- cli_commands: Specific CLI commands for validation
- monitoring_setup: Monitoring and alerting configuration
- validation_procedures: Step-by-step validation procedures

For non-applicable controls, provide:
- id: Control identifier
- name: Control name
- reason: Detailed explanation of why this control doesn't apply to {service_name}

IMPORTANT: Every applicable control MUST include ALL 25 fields listed above. Do not leave any fields empty - provide meaningful content for each field.
"""
        
        logger.info(f"Calling Bedrock with Instructor using model: {RAG_MODEL_ID}")
        
        # Use Instructor for structured output - same pattern as diagram analysis
        response: ServiceControlsMapping = instructor_client.messages.create(
            model=RAG_MODEL_ID,
            max_tokens=4096,
            temperature=0,
            response_model=ServiceControlsMapping,
            messages=[
                {
                    "role": "user",
                    "content": structured_prompt
                }
            ]
        )
        
        logger.info("Bedrock API call with Instructor successful")
        logger.debug(f"Found {len(response.applicable_controls)} applicable and {len(response.non_applicable_controls)} non-applicable controls")
        logger.debug(f"Total controls processed: {response.total_controls_count}")
        
        # Validate response structure
        if not hasattr(response, 'applicable_controls') or not hasattr(response, 'non_applicable_controls'):
            logger.error("Invalid response structure from Instructor")
            raise Exception("Invalid response structure")
        
        # Convert Pydantic model to dict for compatibility with existing code
        result = response.model_dump()
        
        response_body = {
            'statusCode': 200,
            'body': json.dumps({
                'result': json.dumps(result)
            })
        }
        
        logger.info(f"Returning structured response: {json.dumps(response_body)}")
        return response_body
        
    except Exception as e:
        logger.error(f"Error during structured controls mapping: {str(e)}")
        logger.debug(traceback.format_exc())
        # Return empty structure on error with proper error indication
        return {
            'statusCode': 500,
            'body': json.dumps({
                'applicable_controls': [],
                'non_applicable_controls': [],
                'error': f'Structured mapping failed: {str(e)}'
            })
        }

def systematic_framework_discovery(query, bedrock_client):
    """Systematic discovery of relevant controls for framework + service"""
    enhanced_query = f"""
    {query}
    
    Requirements:
    1. Identify ALL relevant control families for this service type
    2. List specific controls within each family
    3. Provide official control requirement text
    4. Assess criticality level (1-10 scale)
    5. Identify measurable compliance criteria
    
    Focus on comprehensive coverage rather than predetermined lists.
    """
    
    logger.info(f"Enhanced query: {enhanced_query[:200]}...")
    
    # Use appropriate model ARN based on account configuration
    model_arn = get_model_arn()
    
    response = retry_retrieve_and_generate(bedrock_client, enhanced_query, model_arn)
    
    logger.info(f"RAG response received, output length: {len(response['output']['text'])}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'result': response['output']['text'],
            'source_documents': response.get('citations', [])
        })
    }

def get_detailed_control_requirements(query, bedrock_client):
    """Get detailed requirements for specific controls"""
    # Use appropriate model ARN based on account configuration
    model_arn = get_model_arn()
    
    response = retry_retrieve_and_generate(bedrock_client, query, model_arn)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'result': response['output']['text'],
            'source_documents': response.get('citations', [])
        })
    }

def standard_rag_query(query, bedrock_client):
    """Standard RAG query for existing functionality"""
    logger.info("Executing standard RAG query")
    # Use appropriate model ARN based on account configuration
    model_arn = get_model_arn()
    
    response = retry_retrieve_and_generate(bedrock_client, query, model_arn)
    
    response_body = {
        'statusCode': 200,
        'body': json.dumps({
            'result': response['output']['text']
        })
    }
    
    logger.info(f"Returning standard RAG response: {json.dumps(response_body)}")
    return response_body
