import json
import os
import boto3
import logging
import uuid
import datetime
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3 = boto3.client('s3')

# Configuration from environment variables
BEDROCK_ACCOUNT_ID = os.environ.get('BEDROCK_ACCOUNT_ID')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID')
BEDROCK_ROLE_NAME = os.environ.get('BEDROCK_ROLE_NAME')
BEDROCK_MAX_TOKENS = int(os.environ.get('BEDROCK_MAX_TOKENS', '40000'))
PROMPTS_BUCKET = os.environ.get('PROMPTS_BUCKET')

# Construct Bedrock role ARN
BEDROCK_ROLE_ARN = f"arn:aws:iam::{BEDROCK_ACCOUNT_ID}:role/{BEDROCK_ROLE_NAME}" if BEDROCK_ACCOUNT_ID and BEDROCK_ROLE_NAME else None

def lambda_handler(event, context):
    """Lambda handler function to invoke Bedrock synchronously"""
    try:
        # Extract service name and prompt from the event
        service_name = event.get('service')
        prompt = event.get('prompt')
        
        logger.info(f"Invoking Bedrock for service: {service_name}")
        
        # Log the full constructed prompt for troubleshooting
        logger.info(f"CONSTRUCTED PROMPT FOR {service_name}:")
        logger.info(f"PROMPT START: {prompt}")
        logger.info(f"PROMPT END")
        
        # Create request body for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": BEDROCK_MAX_TOKENS,
            "temperature": 0.0,   # Minimum temperature for maximum determinism
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Create Bedrock client with cross-account role assumption if configured
        if BEDROCK_ROLE_ARN:
            # Assume cross-account role for Bedrock access
            sts = boto3.client('sts')
            assumed_role = sts.assume_role(
                RoleArn=BEDROCK_ROLE_ARN,
                RoleSessionName=f"bedrock-invoke-{uuid.uuid4()}"
            )
            
            credentials = assumed_role['Credentials']
            bedrock_runtime = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                config=Config(
                    read_timeout=840,  # 14 minutes (leaving 1 minute buffer for the rest of the function)
                    connect_timeout=10,
                    retries={'max_attempts': 2}
                )
            )
        else:
            # Use default credentials
            bedrock_runtime = boto3.client(
                'bedrock-runtime',
                config=Config(
                    read_timeout=840,  # 14 minutes (leaving 1 minute buffer for the rest of the function)
                    connect_timeout=10,
                    retries={'max_attempts': 2}
                )
            )
        
        # Use model ID from environment variable
        model_id = BEDROCK_MODEL_ID or "us.anthropic.claude-sonnet-4-6"
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode())
        content = response_body.get('content', [{}])[0].get('text', '')
        
        logger.info(f"Received response from Bedrock for {service_name}, length: {len(content)}")
        
        # Save the response to S3
        output_key = f"bedrock-results/{service_name}-{uuid.uuid4()}.json"
        s3.put_object(
            Bucket=PROMPTS_BUCKET,
            Key=output_key,
            Body=content,
            ContentType="application/json"
        )
        
        logger.info(f"Saved response to S3: {output_key}")
        
        # Return the result for the next step
        return {
            'service': service_name,
            'result': {
                'content': content,
                'outputLocation': output_key
            }
        }
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {e}")
        raise