import json
import logging
import boto3
from botocore.config import Config
import os
import re
import uuid
from datetime import datetime

BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_framework_filter(framework):
    """Get S3 prefix-based filter for framework-specific documents"""
    framework_prefixes = {
        'nist': 'nist-800-53/',
        'iso27001': 'iso-27001/',
        'soc2': 'sox/',
        'pci_dss': 'pci-dss/',
        'cis': 'cis-controls/',
        'apra_cps234': 'cps234/',
        'ci_profile': 'ci-profile/',
        'cri': 'cri/'
    }
    
    prefix = framework_prefixes.get(framework.lower())
    if not prefix:
        logger.warning(f"Unknown framework: {framework}, no filtering applied")
        return None
    
    return {
        "stringContains": {
            "key": "x-amz-bedrock-kb-source-uri",
            "value": prefix
        }
    }

def lambda_handler(event, context):
    """Discover framework controls and organize into control families"""
    try:
        service_name = event.get('service')
        framework = event.get('framework')
        
        logger.info(f"Discovering {framework} controls for {service_name}")
        
        # Bedrock Knowledge Base configuration
        knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        logger.info(f"KNOWLEDGE_BASE_ID: {knowledge_base_id}")
        logger.info(f"REGION: {region}")
        
        if not knowledge_base_id:
            raise ValueError("KNOWLEDGE_BASE_ID environment variable not set")
        
        # Create Bedrock Runtime client for service description
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        logger.info("Created Bedrock Runtime client")
        
        # Step 1: Get service characteristics from Bedrock
        service_query = f"Describe {service_name} service in one short paragraph focusing on its core function and key characteristics."
        logger.info(f"SERVICE QUERY: {service_query}")
        
        service_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": service_query}]
        }
        
        service_response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(service_request)
        )
        
        service_result = json.loads(service_response['body'].read().decode())
        service_description = service_result.get('content', [{}])[0].get('text', '')
        logger.info(f"SERVICE DESCRIPTION: {service_description}")
        
        # Step 2: Use service description to get framework controls via retrieve-and-generate
        bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=region, config=Config(read_timeout=300, connect_timeout=10, retries={'max_attempts': 0}))
        logger.info("Created Bedrock Agent Runtime client")
        
        # User prompt - what we want to know
        user_prompt = f"""
        What {framework} security control families and individual controls apply to this service: {service_description}?
        
        FRAMEWORK EXAMPLES:
        - NIST: Use codes like "AC", "AU", "IA" for family_code and "AC-1", "AU-2", "IA-3" for individual_controls
        - SOC2: Use codes like "CC6", "CC7", "CC8" for family_code and "CC6.1", "CC6.2", "CC7.1" for individual_controls  
        - ISO27001: Use codes like "A.9", "A.12", "A.13" for family_code and "A.9.1.1", "A.9.1.2", "A.12.1.1" for individual_controls
        - PCI_DSS: Use codes like "REQ1", "REQ2", "REQ3" for family_code and "1.1", "1.2", "2.1" for individual_controls
        - CIS: Use codes like "CIS1", "CIS2", "CIS3" for family_code and "1.1", "1.2", "2.1" for individual_controls
        - APRA_CPS234: Use codes like "CPS1", "CPS2", "CPS3" for family_code and "CPS234.1", "CPS234.2" for individual_controls
        - CRI: Use codes like "GV", "ID", "PR", "DE", "RS", "RC" for family_code and "GV.OV-01", "GV.RM-02", "ID.AM-01", "PR.AC-01", "DE.CM-01" for individual_controls
        """
        
        # Generation prompt - how to format the response
        generation_prompt = f"""
        Based on the search results: $search_results$
        
        YOU MUST return your response ONLY as valid JSON with this EXACT structure. Do not include any other text, explanations, or formatting:

        {{
          "control_families": [
            {{
              "family_name": "actual family name from {framework} framework",
              "family_code": "actual family code from {framework} framework",
              "family_summary": "A paragraph summarizing this control family's diagnostic statements, key requirements, scope, and what it covers in the context of cloud services and cybersecurity",
              "individual_controls": ["list of actual control IDs from {framework}"],
              "description": "brief description of this control family",
              "control_count": number_of_controls
            }}
          ]
        }}

        REQUIREMENTS:
        - Return ONLY valid JSON, no other text
        - Use actual {framework} control naming conventions from the search results
        - Include ALL relevant control families for this service type
        - Each family must have actual {framework} control IDs
        - Do not convert to other frameworks
        - Do not add explanatory text before or after the JSON

        JSON RESPONSE ONLY:
        """
        logger.info(f"USER PROMPT: {user_prompt}")
        logger.info(f"GENERATION PROMPT: {generation_prompt}")
        
        # Build model ARN - inference profiles use account-scoped ARN format
        if BEDROCK_MODEL_ID.startswith(('us.', 'eu.', 'global.', 'ap.')):
            account_id = boto3.client('sts').get_caller_identity()['Account']
            model_arn = f"arn:aws:bedrock:{region}:{account_id}:inference-profile/{BEDROCK_MODEL_ID}"
        else:
            model_arn = f"arn:aws:bedrock:{region}::foundation-model/{BEDROCK_MODEL_ID}"
        
        # Get framework-specific filter
        retrieval_filter = get_framework_filter(framework)
        logger.info(f"FRAMEWORK FILTER: {retrieval_filter}")
        
        # Build retrieval configuration with optional filtering
        retrieval_config = {
            'vectorSearchConfiguration': {
                'numberOfResults': 100,  # Increased from 50 to 100
                'overrideSearchType': 'HYBRID'  # Use hybrid search (semantic + text)
            }
        }
        
        # Add filter if available
        if retrieval_filter:
            retrieval_config['vectorSearchConfiguration']['filter'] = retrieval_filter
        
        response = bedrock_agent.retrieve_and_generate(
            input={
                'text': user_prompt
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': model_arn,
                    'retrievalConfiguration': retrieval_config,
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': generation_prompt
                        },
                        'inferenceConfig': {
                            'textInferenceConfig': {
                                'maxTokens': 8192
                            }
                        }
                    }
                }
            }
        )
        
        controls_text = response.get('output', {}).get('text', '')
        logger.info(f"CONTROLS RESPONSE: {controls_text}")
        
        # Parse the JSON response from AI
        control_families = parse_ai_response(controls_text, framework)
        
        logger.info(f"Found {len(control_families)} control families")
        
        # Prepare data for storage
        result_data = {
            'service': service_name,
            'framework': framework,
            'control_families': control_families,
            'controls_text': controls_text
        }
        
        # Store in S3 if data is large, otherwise return directly
        data_size = len(json.dumps(result_data))
        logger.info(f"Data size: {data_size} bytes ({data_size/1024:.1f} KB)")
        if data_size > 200000:  # 200KB threshold - Step Functions supports up to 256KB
            logger.info("Data exceeds 200KB threshold, storing in S3")
            s3_result = store_results_in_s3(result_data, service_name, framework)
            return {
                'statusCode': 200,
                'body': json.dumps(s3_result)
            }
        else:
            logger.info("Data under 5KB threshold, returning directly")
            return {
                'statusCode': 200,
                'body': json.dumps(result_data)
            }
        
    except Exception as e:
        logger.error(f"Error discovering framework controls: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def parse_ai_response(controls_text, framework):
    """Parse AI response that should contain JSON structure"""
    
    try:
        import re
        
        # Strip markdown code fences
        text = controls_text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        
        # Find JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Handle truncated JSON — find the last complete object in control_families array
                families_match = re.search(r'"control_families"\s*:\s*\[', json_str)
                if families_match:
                    # Find all complete family objects
                    family_pattern = re.finditer(r'\{[^{}]*"family_name"[^{}]*"individual_controls"\s*:\s*\[[^\]]*\][^{}]*\}', json_str)
                    families = []
                    for m in family_pattern:
                        try:
                            families.append(json.loads(m.group(0)))
                        except json.JSONDecodeError:
                            continue
                    if families:
                        logger.info(f"Recovered {len(families)} families from truncated JSON")
                        return families
                parsed_data = {}
            
            if 'control_families' in parsed_data:
                logger.info(f"Successfully parsed JSON response with {len(parsed_data['control_families'])} families")
                return parsed_data['control_families']
        
        # If JSON parsing fails, try to extract structured data from text
        logger.warning("JSON parsing failed, attempting text parsing")
        return parse_text_fallback(text, framework)
        
    except Exception as e:
        logger.error(f"Error parsing AI response: {e}")
        # Return empty list instead of hardcoded fallback
        return []

def parse_text_fallback(controls_text, framework):
    """Fallback text parsing when JSON parsing fails"""
    
    control_families = []
    
    # Split text into sections and try to extract family information
    lines = controls_text.split('\n')
    current_family = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for family headers (various formats)
        if any(keyword in line.lower() for keyword in ['family:', 'control family', 'category:']):
            if current_family:
                control_families.append(current_family)
            
            current_family = {
                'family_name': line.replace('Family:', '').replace('Control Family:', '').replace('Category:', '').strip(),
                'family_code': '',
                'individual_controls': [],
                'description': '',
                'control_count': 0
            }
        
        # Look for control IDs in the line (framework agnostic)
        elif current_family:
            # Extract any alphanumeric control patterns
            control_patterns = re.findall(r'\b[A-Z]{1,3}[-.]?\d+(?:\.\d+)*\b', line)
            if control_patterns:
                current_family['individual_controls'].extend(control_patterns)
    
    # Add the last family
    if current_family:
        current_family['control_count'] = len(current_family['individual_controls'])
        control_families.append(current_family)
    
    logger.info(f"Text fallback parsing found {len(control_families)} families")
    return control_families



def store_results_in_s3(data, service_name, framework):
    """Store large results in S3 and return S3 key"""
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('TEMP_DATA_BUCKET')
        
        if not bucket_name:
            logger.warning("TEMP_DATA_BUCKET not set, returning data directly")
            return {"body": json.dumps(data)}
        
        # Generate unique key
        execution_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"executions/{execution_id}/framework_controls_{service_name}_{framework}_{timestamp}.json"
        
        # Store in S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data),
            ContentType='application/json'
        )
        
        logger.info(f"Stored framework controls in S3: s3://{bucket_name}/{s3_key}")
        
        return {
            "s3_bucket": bucket_name,
            "s3_key": s3_key,
            "data_size": len(json.dumps(data)),
            "stored_in_s3": True
        }
        
    except Exception as e:
        logger.error(f"Failed to store in S3: {str(e)}")
        # Fallback to direct return
        return {"body": json.dumps(data)}