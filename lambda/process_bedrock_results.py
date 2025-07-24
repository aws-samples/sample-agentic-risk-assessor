import json
import os
import boto3
import logging
import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
TABLE_NAME = os.environ.get('SERVICE_CONTROLS_TABLE')
PROMPTS_BUCKET = os.environ.get('PROMPTS_BUCKET')

def normalize_bedrock_control(control, service_name):
    """
    Normalize Bedrock control response to consistent schema while preserving all analysis fields
    """
    # Basic required fields
    normalized = {
        'id': control.get('id') or control.get('control') or control.get('Control', ''),
        'category': control.get('category') or control.get('Category', ''),
        'priority': control.get('priority') or control.get('rating') or control.get('Rating') or control.get('criticality', ''),
        'name': control.get('name') or control.get('Description') or '',
    }
    
    # Normalize description field from service-specific capability fields
    description = (control.get(f'{service_name.lower()}_capability') or
                  control.get(f'{service_name.lower()}Capability') or
                  control.get(f'{service_name.lower()}capability') or
                  control.get('lambda_capability') or
                  control.get('ec2_capability') or
                  control.get('s3_capability') or
                  control.get('rds_capability') or
                  control.get('iam_capability') or
                  control.get('sqs_capability') or
                  control.get('snsCapability') or
                  control.get('vpc_capability') or
                  control.get('elbCapability') or
                  control.get('cloudFormationCapability') or
                  control.get('description') or 
                  control.get('Description') or
                  control.get('Capability') or
                  '')
    
    normalized['description'] = description
    
    # Handle non-applicable controls
    if 'reason' in control or 'Reason' in control:
        normalized['reason'] = control.get('reason') or control.get('Reason', '')
    
    # Preserve all comprehensive analysis fields
    comprehensive_fields = [
        'requirement', 'capabilities', 'implementation_approach',
        'automated_checks', 'measurable_thresholds', 'audit_evidence',
        'criticality_score', 'complexity', 'cost_category',
        'basic_level', 'managed_level', 'optimized_level', 'predictive_level',
        'prerequisites', 'enablers', 'conflicts',
        'cli_commands', 'monitoring_setup', 'validation_procedures'
    ]
    
    for field in comprehensive_fields:
        if field in control:
            normalized[field] = control[field]
    
    return normalized

def lambda_handler(event, context):
    """Lambda handler function to process Bedrock results"""
    try:
        # Extract service name, framework, and result from the event
        service_name = event.get('service')
        framework = event.get('framework')
        
        if not framework:
            logger.error('Framework is required')
            return {'error': 'Framework selection is required'}
        
        result = event.get('result', {})
        
        # DEBUG: Log what we receive raw
        logger.info(f"DEBUG - Raw result received: {json.dumps(result)}")
        
        # Handle the new data structure from invoke_bedrock_rag
        if 'statusCode' in result and 'body' in result:
            # Parse the JSON body from invoke_bedrock_rag response
            try:
                body_data = json.loads(result['body'])
                # The result field contains plain text response, not JSON
                content_str = body_data.get('result', '')
                # Don't try to parse as JSON - it's plain text
                content = content_str
                output_location = ''
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing result body: {e}")
                content = ''
                output_location = ''
        else:
            # Fallback to old structure
            content = result.get('content', '')
            output_location = result.get('outputLocation', '')
        
        logger.info(f"Extracted parameters: service={service_name}, framework={framework}, has_result={bool(result)}")
        
        logger.info(f"Processing results for service: {service_name} with framework: {framework}")
        logger.info(f"Output location: {output_location}")
        logger.info(f"Full event received: {json.dumps(event)}")
        
        # If we have an output location but no content, read from S3
        if output_location and not content:
            try:
                file_response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=output_location)
                content = file_response['Body'].read().decode('utf-8')
                logger.info(f"Read content from S3: {content[:200]}...")
            except Exception as e:
                logger.error(f"Error reading from S3: {e}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': f"Error reading from S3: {str(e)}"})
                }
        
        # Clean the content first to remove markdown formatting (only if it's a string)
        if isinstance(content, str):
            clean_content = content.strip()
            if clean_content.startswith('```json'):
                clean_content = clean_content[7:]  # Remove ```json
            if clean_content.endswith('```'):
                clean_content = clean_content[:-3]  # Remove ```
            clean_content = clean_content.strip()
        else:
            clean_content = content  # Already parsed dict
        
        # Try to parse the content - it might already be parsed JSON from new structure
        try:
            if isinstance(content, dict):
                # Content is already parsed JSON from new structure
                data = content
            else:
                # Content is string, parse as JSON
                data = json.loads(clean_content)
            
            # Process the data
            applicable_controls = []
            non_applicable_controls = []
            
            # Handle different JSON structures and normalize
            if isinstance(data, list):
                # Handle array format
                applicable_controls = [normalize_bedrock_control(control, service_name) for control in data]
            elif 'NIST 800-53 Controls' in data:
                # Handle structured format
                applicable_controls = [normalize_bedrock_control(control, service_name) for control in data.get('NIST 800-53 Controls', [])]
                non_applicable_controls = [normalize_bedrock_control(control, service_name) for control in data.get('Excluded Controls', [])]
            elif 'ControlMappings' in data:
                applicable_controls = [normalize_bedrock_control(control, service_name) for control in data.get('ControlMappings', [])]
            elif 'applicable_controls' in data:
                applicable_controls = [normalize_bedrock_control(control, service_name) for control in data.get('applicable_controls', [])]
                non_applicable_controls = [normalize_bedrock_control(control, service_name) for control in data.get('non_applicable_controls', [])]
            
            # DEBUG: Log what we're about to save
            logger.info(f"DEBUG - About to save {len(applicable_controls)} applicable controls")
            if applicable_controls:
                logger.info(f"DEBUG - First control keys: {list(applicable_controls[0].keys())}")
            
            # Replace empty string values with "N/A" for DynamoDB
            def clean_for_dynamodb(controls):
                cleaned = []
                for control in controls:
                    cleaned_control = {}
                    for key, value in control.items():
                        if value == "" or value is None:
                            cleaned_control[key] = "N/A"  # Replace empty with N/A
                        else:
                            cleaned_control[key] = value
                    cleaned.append(cleaned_control)
                return cleaned
            
            applicable_controls_clean = clean_for_dynamodb(applicable_controls)
            non_applicable_controls_clean = clean_for_dynamodb(non_applicable_controls)
            
            logger.info(f"DEBUG - After cleaning, first control keys: {list(applicable_controls_clean[0].keys()) if applicable_controls_clean else 'None'}")
            
            # Store results in DynamoDB with composite key
            table = dynamodb.Table(TABLE_NAME)
            table.update_item(
                Key={
                    'ServiceName': service_name,
                    'Framework': framework
                },
                UpdateExpression="set ApplicableControls = :a, NonApplicableControls = :n, #status = :s, OutputLocation = :o, ProcessedAt = :p",
                ExpressionAttributeNames={
                    '#status': 'Status'
                },
                ExpressionAttributeValues={
                    ':a': applicable_controls_clean,
                    ':n': non_applicable_controls_clean,
                    ':s': 'COMPLETED',
                    ':o': output_location,
                    ':p': datetime.datetime.now().isoformat()
                }
            )
            
            logger.info(f"Successfully processed and stored results for {service_name}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'service': service_name,
                    'status': 'COMPLETED',
                    'message': 'Service mapping completed successfully'
                })
            }
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON directly: {e}")
            
            # Try to extract JSON from markdown code blocks
            try:
                clean_content = content.replace('```json', '').replace('```', '')
                data = json.loads(clean_content)
                
                # Process the data
                applicable_controls = []
                non_applicable_controls = []
                
                if isinstance(data, list):
                    applicable_controls = data
                    for control in applicable_controls:
                        if 'control' in control:
                            control['id'] = control.pop('control')
                        if 's3Capability' in control:
                            control['description'] = control.pop('s3Capability')
                        if 'ec2Capability' in control:
                            control['description'] = control.pop('ec2Capability')
                        if 'rdsCapability' in control:
                            control['description'] = control.pop('rdsCapability')
                        if 'lambdaCapability' in control:
                            control['description'] = control.pop('lambdaCapability')
                        if 'iamCapability' in control:
                            control['description'] = control.pop('iamCapability')
                        if 'rating' in control:
                            control['priority'] = control.pop('rating')
                        if 'category' in control:
                            control['category'] = control.pop('category')
                
                # Store results in DynamoDB with composite key
                table = dynamodb.Table(TABLE_NAME)
                table.update_item(
                    Key={
                        'ServiceName': service_name,
                        'Framework': framework
                    },
                    UpdateExpression="set ApplicableControls = :a, NonApplicableControls = :n, #status = :s, OutputLocation = :o, ProcessedAt = :p",
                    ExpressionAttributeNames={
                        '#status': 'Status'
                    },
                    ExpressionAttributeValues={
                        ':a': applicable_controls,
                        ':n': non_applicable_controls,
                        ':s': 'COMPLETED',
                        ':o': output_location,
                        ':p': datetime.datetime.now().isoformat()
                    }
                )
                
                logger.info(f"Successfully processed and stored results for {service_name} after cleaning markdown")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'service': service_name,
                        'status': 'COMPLETED',
                        'message': 'Service mapping completed successfully'
                    })
                }
            except Exception as e2:
                logger.error(f"Error parsing cleaned content: {e2}")
                
                # Try to extract JSON from the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    try:
                        data = json.loads(json_str)
                        
                        # Process the data
                        applicable_controls = []
                        non_applicable_controls = []
                        
                        # Handle different JSON structures from Bedrock
                        if 'ControlMappings' in data:
                            applicable_controls = data.get('ControlMappings', [])
                        elif 'applicable_controls' in data:
                            applicable_controls = data.get('applicable_controls', [])
                            non_applicable_controls = data.get('non_applicable_controls', [])
                        elif 'NIST 800-53 Controls' in data:
                            # Handle the EC2 format
                            applicable_controls = data.get('NIST 800-53 Controls', [])
                            # Map the fields to match the expected format
                            for control in applicable_controls:
                                if 'Control' in control:
                                    control['id'] = control.pop('Control')
                                if 'Description' in control:
                                    control['name'] = control.pop('Description')
                                if 'Capability' in control:
                                    control['description'] = control.pop('Capability')
                                if 'Category' in control:
                                    control['category'] = control.pop('Category')
                                if 'Rating' in control:
                                    control['priority'] = control.pop('Rating')
                            
                            # Handle excluded controls if present
                            if 'Excluded Controls' in data:
                                non_applicable_controls = data.get('Excluded Controls', [])
                                for control in non_applicable_controls:
                                    if 'Control' in control:
                                        control['id'] = control.pop('Control')
                                    if 'Description' in control:
                                        control['name'] = control.pop('Description')
                                    if 'Reason' in control:
                                        control['reason'] = control.pop('Reason')
                        else:
                            # Try to parse array format (like S3 response)
                            try:
                                # If the content is an array, it might be directly the controls
                                array_data = json.loads(content.strip().replace('```json', '').replace('```', ''))
                                if isinstance(array_data, list):
                                    applicable_controls = array_data
                                    # Standardize field names
                                    for control in applicable_controls:
                                        if 'control' in control:
                                            control['id'] = control.pop('control')
                                        if 's3Capability' in control:
                                            control['description'] = control.pop('s3Capability')
                                        if 'ec2Capability' in control:
                                            control['description'] = control.pop('ec2Capability')
                                        if 'rdsCapability' in control:
                                            control['description'] = control.pop('rdsCapability')
                                        if 'lambdaCapability' in control:
                                            control['description'] = control.pop('lambdaCapability')
                                        if 'iamCapability' in control:
                                            control['description'] = control.pop('iamCapability')
                                        if 'rating' in control:
                                            control['priority'] = control.pop('rating')
                                        if 'category' in control:
                                            control['category'] = control.pop('category')
                            except Exception as e:
                                logger.error(f"Failed to parse array format: {e}")
                        
                        # Store results in DynamoDB with composite key
                        table = dynamodb.Table(TABLE_NAME)
                        table.update_item(
                            Key={
                                'ServiceName': service_name,
                                'Framework': framework
                            },
                            UpdateExpression="set ApplicableControls = :a, NonApplicableControls = :n, #status = :s, OutputLocation = :o, ProcessedAt = :p",
                            ExpressionAttributeNames={
                                '#status': 'Status'
                            },
                            ExpressionAttributeValues={
                                ':a': applicable_controls,
                                ':n': non_applicable_controls,
                                ':s': 'COMPLETED',
                                ':o': output_location,
                                ':p': datetime.datetime.now().isoformat()
                            }
                        )
                        
                        logger.info(f"Successfully processed and stored results for {service_name}")
                        return {
                            'statusCode': 200,
                            'body': json.dumps({
                                'service': service_name,
                                'status': 'COMPLETED',
                                'message': 'Service mapping completed successfully'
                            })
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON from response: {e}")
                        return {
                            'statusCode': 500,
                            'body': json.dumps({
                                'error': f"Failed to parse JSON: {str(e)}"
                            })
                        }
                else:
                    logger.error("No JSON found in response")
                    return {
                        'statusCode': 500,
                        'body': json.dumps({
                            'error': "No JSON found in response"
                        })
                    }
    except Exception as e:
        logger.error(f"Error processing results: {e}")
        logger.error(f"Event that caused error: {json.dumps(event)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }