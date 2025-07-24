import json
import os
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Configuration
TABLE_NAME = os.environ.get('SERVICE_CONTROLS_TABLE')
RESULTS_QUEUE_URL = os.environ.get('RESULTS_QUEUE_URL')
PROMPTS_BUCKET = os.environ.get('PROMPTS_BUCKET')

def parse_bedrock_response(response_text):
    """Parse the Bedrock response to extract applicable and non-applicable controls"""
    try:
        # Extract JSON from the response text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            logger.error("No JSON found in response")
            return {"applicable_controls": [], "non_applicable_controls": []}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from response: {e}")
        return {"applicable_controls": [], "non_applicable_controls": []}

def save_to_dynamodb(service_name, applicable_controls, non_applicable_controls):
    """Save the results to DynamoDB"""
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        table.update_item(
            Key={'ServiceName': service_name},
            UpdateExpression="set ApplicableControls = :a, NonApplicableControls = :n, Status = :s",
            ExpressionAttributeValues={
                ':a': applicable_controls,
                ':n': non_applicable_controls,
                ':s': 'COMPLETED'
            }
        )
        return True
    except ClientError as e:
        logger.error(f"Error saving to DynamoDB: {e}")
        return False

def lambda_handler(event, context):
    """Lambda handler function for processing SQS messages with Bedrock results"""
    try:
        for record in event['Records']:
            # Parse the message
            message = json.loads(record['body'])
            service_name = message.get('service_name')
            output_key = message.get('output_key')
            
            logger.info(f"Processing results for service: {service_name}, output key: {output_key}")
            
            # Get the result from S3
            response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=output_key)
            response_text = response['Body'].read().decode('utf-8')
            
            # Parse the response
            parsed_response = parse_bedrock_response(response_text)
            
            # Save to DynamoDB
            applicable_controls = parsed_response.get('applicable_controls', [])
            non_applicable_controls = parsed_response.get('non_applicable_controls', [])
            
            logger.info(f"Found {len(applicable_controls)} applicable controls and {len(non_applicable_controls)} non-applicable controls for {service_name}")
            
            save_result = save_to_dynamodb(service_name, applicable_controls, non_applicable_controls)
            
            if save_result:
                logger.info(f"Successfully processed and saved results for {service_name}")
            else:
                logger.error(f"Failed to save results for {service_name}")
                
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Successfully processed results'})
        }
    except Exception as e:
        logger.error(f"Error processing results: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }