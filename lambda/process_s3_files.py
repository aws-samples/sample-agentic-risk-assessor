import json
import os
import boto3
import logging
import datetime
import re
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
TABLE_NAME = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service-controls')
PROMPTS_BUCKET = os.environ.get('APP_DATA_BUCKET')

def extract_json_array(content):
    """Extract JSON array from content with markdown formatting"""
    # Remove markdown formatting
    clean_content = content.replace('```json', '').replace('```', '').strip()
    
    # Check if the content is already a valid JSON array
    if clean_content.startswith('[') and clean_content.endswith(']'):
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse clean content as JSON: {e}")
    
    # Look for array pattern
    array_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
    if array_match:
        try:
            array_str = array_match.group(0)
            return json.loads(array_str)
        except Exception as e:
            logger.error(f"Failed to parse regex match as JSON: {e}")
    
    # If regex fails, try bracket matching
    if '[' in content and ']' in content:
        try:
            start = content.find('[')
            # Find the matching closing bracket
            count = 1
            for i in range(start + 1, len(content)):
                if content[i] == '[':
                    count += 1
                elif content[i] == ']':
                    count -= 1
                    if count == 0:
                        end = i + 1
                        break
            
            if count == 0:
                array_str = content[start:end]
                return json.loads(array_str)
        except Exception as e:
            logger.error(f"Failed to parse bracket match as JSON: {e}")
    
    return None

def process_s3_file(service_name, output_location):
    """Process a file directly from S3"""
    try:
        logger.info(f"Processing S3 file for {service_name}: {output_location}")
        
        # Get the file content
        file_response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=output_location)
        content = file_response['Body'].read().decode('utf-8')
        logger.info(f"Successfully read file from S3: {output_location}")
        logger.info(f"Content preview: {content[:200]}...")
        
        # Try to parse as JSON directly
        applicable_controls = []
        non_applicable_controls = []
        
        # First try to extract JSON array
        array_data = extract_json_array(content)
        if array_data and isinstance(array_data, list):
            logger.info(f"Successfully extracted JSON array with {len(array_data)} items")
            applicable_controls = array_data
        else:
            # If array extraction fails, try direct parsing
            try:
                # Clean up markdown formatting
                clean_content = content.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_content)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    applicable_controls = data
                    logger.info(f"Successfully parsed JSON list with {len(applicable_controls)} items")
                elif 'NIST 800-53 Controls' in data:
                    applicable_controls = data.get('NIST 800-53 Controls', [])
                    logger.info(f"Found NIST 800-53 Controls with {len(applicable_controls)} items")
                    if 'Excluded Controls' in data:
                        non_applicable_controls = data.get('Excluded Controls', [])
                elif 'ControlMappings' in data:
                    applicable_controls = data.get('ControlMappings', [])
                    logger.info(f"Found ControlMappings with {len(applicable_controls)} items")
                elif 'applicable_controls' in data:
                    applicable_controls = data.get('applicable_controls', [])
                    non_applicable_controls = data.get('non_applicable_controls', [])
                    logger.info(f"Found applicable_controls with {len(applicable_controls)} items")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse content as JSON: {e}")
        
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
        
        for control in non_applicable_controls:
            if 'Control' in control:
                control['id'] = control.pop('Control')
            if 'Description' in control:
                control['name'] = control.pop('Description')
            if 'Reason' in control:
                control['reason'] = control.pop('Reason')
        
        # Update DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.update_item(
            Key={'ServiceName': service_name},
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
        
        logger.info(f"Successfully updated DynamoDB for service {service_name} with {len(applicable_controls)} controls")
        return True
    except Exception as e:
        logger.error(f"Error processing S3 file {output_location}: {e}")
        return False

def lambda_handler(event, context):
    """Lambda handler function triggered by Step Functions"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract service name and output location from the event
        service_name = event.get('service')
        output_location = event.get('outputLocation')
        
        if service_name and output_location:
            logger.info(f"Processing file for service {service_name}: {output_location}")
            process_s3_file(service_name, output_location)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully processed file for service {service_name}',
                    'service': service_name
                })
            }
        
        # If we don't have service and output location, return an error
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing service or outputLocation'})
        }
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }