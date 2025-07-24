import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Retrieve framework controls data from S3 for Step Function processing
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")
        
        # Extract S3 information from the event
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        
        if not s3_bucket or not s3_key:
            raise ValueError("Missing s3_bucket or s3_key in event")
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Retrieve the object from S3
        logger.info(f"Retrieving s3://{s3_bucket}/{s3_key}")
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        
        # Parse the JSON content
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)
        
        logger.info(f"Retrieved {len(content)} bytes from S3")
        logger.info(f"Found {len(data.get('control_families', []))} control families")
        
        return {
            'statusCode': 200,
            'body': json.dumps(data)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving S3 data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
