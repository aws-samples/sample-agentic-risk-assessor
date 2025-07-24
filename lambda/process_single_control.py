import json
import boto3
import logging
import os
import time
import uuid
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
from botocore.config import Config
bedrock_config = Config(
    read_timeout=300,
    connect_timeout=10,
    retries={'max_attempts': 0}
)
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1', config=bedrock_config)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3_client = boto3.client('s3')

def load_from_s3_if_needed(data):
    """Load data from S3 if it's stored there, otherwise return as-is"""
    if isinstance(data, dict):
        # Check if this is a Lambda response object
        if 'statusCode' in data and 'body' in data:
            try:
                # Parse the body from Lambda response
                body_content = data['body']
                if isinstance(body_content, str):
                    return json.loads(body_content)
                return body_content
            except Exception as e:
                logger.error(f"Failed to parse Lambda response body: {str(e)}")
                return data
        
        # Check if it's S3 stored data
        if data.get('stored_in_s3'):
            try:
                bucket = data['s3_bucket']
                key = data['s3_key']
                
                logger.info(f"Loading data from S3: s3://{bucket}/{key}")
                
                response = s3_client.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read().decode('utf-8')
                return json.loads(content)
                
            except Exception as e:
                logger.error(f"Failed to load from S3: {str(e)}")
                return data
    
    return data

def lambda_handler(event, context):
    """
    Process a single control with comprehensive implementation guidance
    """
    try:
        handler_start = time.time()
        logger.info(f"Processing single control: service={event.get('service')}, framework={event.get('framework')}, control_id={event.get('control_id')}")
        
        # Extract parameters
        service = event.get('service')
        framework = event.get('framework')
        control_id = event.get('control_id')
        # Support both old format (control_id is string) and new format (control_item is object)
        if isinstance(control_id, dict):
            # Old step function passed the whole object as control_id
            control_name = control_id.get('name', '')
            diagnostic_statement = control_id.get('diagnostic_statement', '')
            control_id = control_id.get('id', str(control_id))
        else:
            control_name = event.get('control_name', '')
            diagnostic_statement = event.get('diagnostic_statement', '')
        control_family = event.get('control_family', {})
        family_capabilities = event.get('family_capabilities', [])
        
        # Load data from S3 if needed
        try:
            t0 = time.time()
            control_family = load_from_s3_if_needed(control_family)
            logger.info(f"[TIMING] load_from_s3 control_family: {time.time()-t0:.3f}s, type={type(control_family).__name__}")
        except Exception as e:
            logger.error(f"Error loading control_family: {str(e)}")
            raise
            
        try:
            t0 = time.time()
            family_capabilities = load_from_s3_if_needed(family_capabilities)
            logger.info(f"[TIMING] load_from_s3 family_capabilities: {time.time()-t0:.3f}s, type={type(family_capabilities).__name__}")
        except Exception as e:
            logger.error(f"Error loading family_capabilities: {str(e)}")
            raise
        
        if not all([service, framework, control_id]):
            raise ValueError("Missing required parameters: service, framework, control_id")
        
        # Create comprehensive prompt for single control
        try:
            t0 = time.time()
            prompt = create_single_control_prompt(
                service=service,
                framework=framework,
                control_id=control_id,
                control_family=control_family,
                family_capabilities=family_capabilities,
                control_name=control_name,
                diagnostic_statement=diagnostic_statement
            )
            logger.info(f"[TIMING] create_prompt: {time.time()-t0:.3f}s, prompt_len={len(prompt)}")
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}")
            raise
        
        # Invoke Bedrock and get structured control mapping
        try:
            t0 = time.time()
            control_mapping = invoke_bedrock_for_control(prompt, control_id, service, framework)
            logger.info(f"[TIMING] invoke_bedrock: {time.time()-t0:.1f}s")
        except Exception as e:
            logger.error(f"[TIMING] invoke_bedrock FAILED after {time.time()-t0:.1f}s: {str(e)}")
            raise
        # Store the control mapping in DynamoDB
        try:
            store_control_mapping(control_mapping, service, framework)
            logger.info(f"Stored control mapping successfully")
        except Exception as e:
            logger.error(f"Error storing control mapping: {str(e)}")
            raise
        
        logger.info(f"Successfully processed control {control_id} for {service}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'control_id': control_id,
                'service': service,
                'framework': framework,
                'status': 'completed',
                'control_mapping': control_mapping
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing single control: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'control_id': event.get('control_id', 'unknown'),
                'service': event.get('service', 'unknown')
            })
        }

def create_single_control_prompt(service, framework, control_id, control_family, family_capabilities, control_name='', diagnostic_statement=''):
    """Create comprehensive prompt for single control processing"""
    
    try:
        family_name = control_family.get('family_name', 'Unknown') if isinstance(control_family, dict) else 'Unknown'
        family_description = control_family.get('description', '') if isinstance(control_family, dict) else ''
        
        # Format capabilities for prompt - handle both dict and list formats
        capabilities_text = ""
        if family_capabilities:
            if isinstance(family_capabilities, dict) and 'service_capabilities' in family_capabilities:
                capabilities_list = family_capabilities['service_capabilities']
            elif isinstance(family_capabilities, list):
                capabilities_list = family_capabilities
            else:
                capabilities_list = []
            
            # Safely extract capability information
            capability_entries = []
            for cap in list(capabilities_list[:10]):  # Limit to avoid token limits
                if isinstance(cap, dict):
                    name = cap.get('name', 'Unknown')
                    description = cap.get('description', '')
                    
                    # Handle compliance_features safely - convert lists to strings
                    compliance_features = cap.get('compliance_features', [])
                    if isinstance(compliance_features, list):
                        # Convert list to comma-separated string
                        features_str = ', '.join(str(f) for f in compliance_features)
                    else:
                        features_str = str(compliance_features)
                    
                    capability_entries.append(f"- {name}: {description} (Features: {features_str})")
            
            capabilities_text = "\n".join(capability_entries)
        
        prompt = f"""Create comprehensive implementation guidance for {framework.upper()} control {control_id} using {service} capabilities.

Control: {control_id}
{f'Control Name: {control_name}' if control_name else ''}
{f'Requirement: {diagnostic_statement}' if diagnostic_statement else ''}
Service: {service}
Framework: {framework.upper()}
Control Family: {family_name}
Family Description: {family_description}

Available {service} Capabilities for {family_name}:
{capabilities_text}

Use the store_control_mapping tool to provide detailed implementation guidance. Use the exact control name and requirement text provided above. Ensure all information is accurate and based on actual AWS capabilities. Focus specifically on {control_id} implementation using the provided {service} capabilities. Provide detailed, actionable content for each field."""
        
        return prompt
        
    except Exception as e:
        logger.error(f"Error in create_single_control_prompt: {str(e)}")
        logger.error(f"control_family type: {type(control_family)}")
        logger.error(f"family_capabilities type: {type(family_capabilities)}")
        
        # Return a basic prompt if there's an error
        return f"""
Create basic implementation guidance for {framework.upper()} control {control_id} using {service} capabilities.

Control: {control_id}
Service: {service}
Framework: {framework.upper()}

Generate detailed mapping with the following structure (return as valid JSON):
{{
    "id": "{control_id}",
    "name": "Control Name",
    "description": "How {service} implements this control",
    "basic_level": "Fundamental implementation steps"
}}
"""

def invoke_bedrock_for_control(prompt, control_id, service, framework):
    """Invoke Bedrock using converse API with tool_use for structured output"""
    
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')
    logger.info(f"Using model: {model_id}")
    
    # Define the tool schema matching our control mapping structure
    tool_def = {
        "toolSpec": {
            "name": "store_control_mapping",
            "description": "Store a structured control mapping with implementation guidance",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Control name"},
                        "category": {"type": "string", "description": "Control category"},
                        "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "description": {"type": "string", "description": "How the service implements this control"},
                        "basic_level": {"type": "string", "description": "Fundamental implementation steps"},
                        "managed_level": {"type": "string", "description": "Enhanced implementation with automation"},
                        "optimized_level": {"type": "string", "description": "Advanced implementation with best practices"},
                        "predictive_level": {"type": "string", "description": "AI/ML-enhanced implementation"},
                        "criticality_score": {"type": "string", "description": "1-10 rating"},
                        "complexity": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "cli_commands": {"type": "string", "description": "Specific AWS CLI commands"},
                        "prerequisites": {"type": "string", "description": "Required services/knowledge"},
                        "conflicts": {"type": "string", "description": "Potential conflicts or limitations"},
                        "implementation_approach": {"type": "string", "description": "Step-by-step guidance"},
                        "capabilities": {"type": "string", "description": "Specific service features used"},
                        "enablers": {"type": "string", "description": "Supporting AWS services"},
                        "audit_evidence": {"type": "string", "description": "What to collect for compliance"},
                        "requirement": {"type": "string", "description": "Official control requirement text"},
                        "cost_category": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "measurable_thresholds": {"type": "string", "description": "Success criteria and metrics"},
                        "validation_procedures": {"type": "string", "description": "How to verify implementation"},
                        "automated_checks": {"type": "string", "description": "AWS Config rules or similar"},
                        "monitoring_setup": {"type": "string", "description": "CloudWatch/logging configuration"}
                    },
                    "required": ["name", "category", "priority", "description", "basic_level",
                                 "managed_level", "optimized_level", "criticality_score", "complexity",
                                 "implementation_approach", "capabilities", "audit_evidence", "requirement"]
                }
            }
        }
    }
    
    t0 = time.time()
    try:
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            toolConfig={"tools": [tool_def], "toolChoice": {"tool": {"name": "store_control_mapping"}}},
            inferenceConfig={"temperature": 0.0}
        )
        
        latency = time.time() - t0
        usage = response.get('usage', {})
        logger.info(f"[BEDROCK] converse returned in {latency:.1f}s, in={usage.get('inputTokens','?')}, out={usage.get('outputTokens','?')}")
        
        # Extract structured tool input from response
        for block in response['output']['message']['content']:
            if 'toolUse' in block:
                mapping = block['toolUse']['input']
                # Add fixed fields
                mapping['id'] = control_id
                mapping['service'] = service
                mapping['framework'] = framework
                # Fill defaults for optional fields
                defaults = {
                    'predictive_level': 'AI-enhanced implementation',
                    'cli_commands': '',
                    'prerequisites': f'{service} service access',
                    'conflicts': 'None identified',
                    'enablers': 'AWS services',
                    'cost_category': 'Medium',
                    'measurable_thresholds': 'Implementation complete',
                    'validation_procedures': 'Verify configuration',
                    'automated_checks': 'AWS Config rules',
                    'monitoring_setup': 'CloudWatch monitoring'
                }
                for k, v in defaults.items():
                    if k not in mapping or not mapping[k]:
                        mapping[k] = v
                return mapping
        
        raise ValueError("No tool_use block in Bedrock response")
        
    except Exception as e:
        logger.error(f"[BEDROCK] converse FAILED after {time.time()-t0:.1f}s: {str(e)}")
        raise

def store_control_mapping(control_mapping, service, framework):
    """Store individual control mapping as its own DynamoDB item"""
    
    table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls')
    table = dynamodb.Table(table_name)
    control_id = control_mapping.get('id', 'unknown')
    
    try:
        # Store as individual item: ServiceName=service, Framework=framework#control_id
        table.put_item(
            Item={
                'ServiceName': service,
                'Framework': f"{framework}#CTRL#{control_id}",
                'ControlData': control_mapping,
                'Status': 'COMPLETE',
                'ProcessedAt': datetime.utcnow().isoformat(),
                'ItemType': 'CONTROL'
            }
        )
        
        logger.info(f"Stored individual control mapping for {control_id} in {service}")
        
    except Exception as e:
        logger.error(f"Failed to store control mapping: {str(e)}")
        raise

def check_and_mark_service_complete(service, framework, total_expected_controls=None):
    """Check if all controls are processed and mark service as complete"""
    
    table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls')
    table = dynamodb.Table(table_name)
    
    try:
        # Get current service record
        response = table.get_item(
            Key={
                'ServiceName': service,
                'Framework': framework
            }
        )
        
        if 'Item' in response:
            item = response['Item']
            applicable_controls = item.get('ApplicableControls', [])
            
            # If we have expected count, check completion
            if total_expected_controls and len(applicable_controls) >= total_expected_controls:
                table.update_item(
                    Key={
                        'ServiceName': service,
                        'Framework': framework
                    },
                    UpdateExpression='SET #status = :complete, CompletedAt = :timestamp',
                    ExpressionAttributeNames={
                        '#status': 'Status'
                    },
                    ExpressionAttributeValues={
                        ':complete': 'COMPLETE',
                        ':timestamp': datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Marked service {service} as COMPLETE for {framework}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to check service completion: {str(e)}")
        return False
