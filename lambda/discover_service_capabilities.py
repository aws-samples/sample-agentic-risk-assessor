import json
import logging
import boto3
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any

BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def discover_service_capabilities(service_name: str, control_family: str = None, family_code: str = None, family_summary: str = '') -> Dict[str, Any]:
    """Discover service capabilities using Bedrock, optionally focused on a control family"""
    try:
        logger.info(f"Discovering capabilities for {service_name} using Bedrock")
        if control_family:
            logger.info(f"Focusing on control family: {control_family} ({family_code})")
        
        # Create Bedrock Runtime client
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Create focused prompt based on control family
        if control_family and family_code:
            summary_context = f"\n\nFamily Summary:\n{family_summary}\n" if family_summary else ""
            prompt = f"""
            List the AWS {service_name} capabilities specifically relevant to {control_family} ({family_code}) security controls.
            {summary_context}
            Focus on {service_name} features that directly support or implement {control_family} requirements.
            
            Provide a structured list with capability names and detailed descriptions of how each capability supports {control_family} controls.
            """
        else:
            prompt = f"List the key security and compliance capabilities of AWS {service_name} service. Focus on features like encryption, access control, monitoring, backup, and compliance. Provide a structured list with capability names and descriptions."
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        logger.info(f"[BEDROCK] Calling invoke_model with modelId={BEDROCK_MODEL_ID}, body_size={len(json.dumps(request_body))}")
        t0 = time.time()
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        logger.info(f"[BEDROCK] invoke_model returned in {time.time()-t0:.3f}s")
        
        response_body = json.loads(response['body'].read().decode())
        content = response_body.get('content', [{}])[0].get('text', '')
        logger.info(f"[BEDROCK] response_len={len(content)}, input_tokens={response_body.get('usage',{}).get('input_tokens','?')}, output_tokens={response_body.get('usage',{}).get('output_tokens','?')}")
        
        # Parse the response to extract capabilities
        capabilities = parse_bedrock_response(service_name, content, control_family, family_code)
        
        result_data = {
            'service': service_name,
            'control_family': control_family,
            'family_code': family_code,
            'service_capabilities': capabilities[:15],
            'capabilities_summary': f"Found {len(capabilities)} capabilities for {service_name}" + (f" relevant to {control_family}" if control_family else " via Bedrock")
        }
        
        return result_data
        
    except Exception as e:
        logger.error(f"Error with Bedrock service capabilities: {e}")
        raise e

def parse_bedrock_response(service_name: str, content: str, control_family: str = None, family_code: str = None) -> List[Dict[str, Any]]:
    """Parse Bedrock response to extract structured capabilities"""
    capabilities = []
    
    # Split content into lines and look for capability patterns
    lines = content.split('\n')
    current_capability = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for capability headers (numbered lists, bullet points, etc.)
        if any(pattern in line.lower() for pattern in ['encryption', 'access control', 'monitoring', 'backup', 'compliance', 'security', 'audit', 'logging', 'iam', 'policy', 'cloudtrail', 'cloudwatch']):
            # Extract capability name and description
            if ':' in line:
                parts = line.split(':', 1)
                name = parts[0].strip('- 1234567890.*').strip()
                description = parts[1].strip() if len(parts) > 1 else f"{service_name} {name.lower()} capability"
            else:
                name = line.strip('- 1234567890.*').strip()
                description = f"{service_name} {name.lower()} capability"
            
            # Determine category and security relevance based on control family
            category = 'security'
            security_relevance = 'high'
            compliance_features = []
            
            name_lower = name.lower()
            
            # Map capabilities to compliance features based on control family
            if family_code == 'AC' or 'access' in name_lower or 'iam' in name_lower or 'policy' in name_lower:
                compliance_features = ['access_control']
            elif family_code == 'AU' or 'audit' in name_lower or 'log' in name_lower or 'monitor' in name_lower or 'cloudtrail' in name_lower:
                compliance_features = ['monitoring']
                category = 'compliance'
                security_relevance = 'medium'
            elif family_code == 'SC' or 'encrypt' in name_lower or 'tls' in name_lower or 'ssl' in name_lower:
                compliance_features = ['encryption']
            elif family_code == 'CP' or 'backup' in name_lower or 'recovery' in name_lower:
                compliance_features = ['data_protection']
            elif family_code == 'IA' or 'identity' in name_lower or 'auth' in name_lower:
                compliance_features = ['authentication']
            elif 'compliance' in name_lower:
                compliance_features = ['compliance']
                category = 'compliance'
            else:
                compliance_features = ['general']
            
            capability = {
                'name': f"{service_name} {name}",
                'description': description,
                'category': category,
                'security_relevance': security_relevance,
                'compliance_features': compliance_features
            }
            capabilities.append(capability)
    
    # If no structured capabilities found, create family-specific basic ones
    if not capabilities:
        capabilities = create_default_capabilities(service_name, control_family, family_code)
    
    return capabilities

def create_default_capabilities(service_name: str, control_family: str = None, family_code: str = None) -> List[Dict[str, Any]]:
    """Create default capabilities based on control family"""
    
    if family_code == 'AC':
        return [
            {
                'name': f'{service_name} IAM Integration',
                'description': f'Integration with AWS Identity and Access Management for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['access_control']
            },
            {
                'name': f'{service_name} Resource Policies',
                'description': f'Resource-based policies for fine-grained access control in {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['access_control']
            },
            {
                'name': f'{service_name} Permission Management',
                'description': f'Permission management and least privilege access for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['access_control']
            }
        ]
    elif family_code == 'AU':
        return [
            {
                'name': f'{service_name} CloudTrail Integration',
                'description': f'AWS CloudTrail logging for {service_name} API calls and activities',
                'category': 'compliance',
                'security_relevance': 'high',
                'compliance_features': ['monitoring']
            },
            {
                'name': f'{service_name} Access Logging',
                'description': f'Detailed access logging and audit trails for {service_name}',
                'category': 'compliance',
                'security_relevance': 'high',
                'compliance_features': ['monitoring']
            },
            {
                'name': f'{service_name} CloudWatch Integration',
                'description': f'CloudWatch metrics and monitoring for {service_name}',
                'category': 'compliance',
                'security_relevance': 'medium',
                'compliance_features': ['monitoring']
            }
        ]
    elif family_code == 'SC':
        return [
            {
                'name': f'{service_name} Encryption at Rest',
                'description': f'Data encryption at rest capabilities for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['encryption']
            },
            {
                'name': f'{service_name} Encryption in Transit',
                'description': f'Data encryption in transit using TLS/SSL for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['encryption']
            },
            {
                'name': f'{service_name} Network Security',
                'description': f'Network security and communication protection for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['network_security']
            }
        ]
    else:
        # Generic capabilities
        return [
            {
                'name': f'{service_name} Security Features',
                'description': f'Built-in security capabilities for {service_name}',
                'category': 'security',
                'security_relevance': 'high',
                'compliance_features': ['general']
            },
            {
                'name': f'{service_name} Compliance Support',
                'description': f'Compliance and governance features for {service_name}',
                'category': 'compliance',
                'security_relevance': 'medium',
                'compliance_features': ['compliance']
            }
        ]

def store_capabilities_in_s3(data, service_name, control_family):
    """Store large capabilities data in S3 and return S3 key"""
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('TEMP_DATA_BUCKET')
        
        if not bucket_name:
            logger.warning("TEMP_DATA_BUCKET not set, returning data directly")
            return data
        
        # Generate unique key
        execution_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"executions/{execution_id}/service_capabilities_{service_name}_{control_family}_{timestamp}.json"
        
        # Store in S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data),
            ContentType='application/json'
        )
        
        logger.info(f"Stored service capabilities in S3: s3://{bucket_name}/{s3_key}")
        
        return {
            "s3_bucket": bucket_name,
            "s3_key": s3_key,
            "data_size": len(json.dumps(data)),
            "stored_in_s3": True,
            "service": service_name,
            "control_family": control_family
        }
        
    except Exception as e:
        logger.error(f"Failed to store capabilities in S3: {str(e)}")
        # Fallback to direct return
        return data

def lambda_handler(event, context):
    """Lambda handler for service capability discovery"""
    try:
        service_name = event.get('service')
        control_family = event.get('control_family')
        family_code = event.get('family_code')
        family_summary = event.get('family_summary', '')
        
        if not service_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Service name is required'})
            }
        
        logger.info(f"Discovering capabilities for service: {service_name}")
        if control_family:
            logger.info(f"Control family: {control_family} ({family_code})")
        
        # Run synchronous function
        result = discover_service_capabilities(service_name, control_family, family_code, family_summary)
        
        # Store in S3 if data is large, otherwise return directly
        data_size = len(json.dumps(result))
        if data_size > 30000:  # 30KB threshold
            s3_result = store_capabilities_in_s3(result, service_name, control_family or 'general')
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps(s3_result)
            }
        else:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps(result)
            }
        
    except Exception as e:
        logger.error(f"Error in discover_service_capabilities: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to discover service capabilities',
                'details': str(e)
            })
        }
