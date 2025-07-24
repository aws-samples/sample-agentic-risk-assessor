import json
import os
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
bedrock = boto3.client('bedrock')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
TABLE_NAME = os.environ.get('SERVICE_CONTROLS_TABLE')
PROMPTS_BUCKET = os.environ.get('PROMPTS_BUCKET')

def parse_bedrock_response(response_text):
    """Parse the Bedrock response to extract applicable and non-applicable controls"""
    try:
        # Extract JSON from the response text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Handle the actual structure with ControlMappings
            if 'ControlMappings' in data:
                return {
                    "applicable_controls": data.get('ControlMappings', []),
                    "non_applicable_controls": []
                }
            else:
                # Try to use the structure as is if it already has our expected fields
                return {
                    "applicable_controls": data.get('applicable_controls', []),
                    "non_applicable_controls": data.get('non_applicable_controls', [])
                }
        else:
            logger.error("No JSON found in response")
            return {"applicable_controls": [], "non_applicable_controls": []}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from response: {e}")
        return {"applicable_controls": [], "non_applicable_controls": []}

def update_dynamodb(service_name, applicable_controls, non_applicable_controls):
    """Update DynamoDB with the results"""
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        table.update_item(
            Key={'ServiceName': service_name},
            UpdateExpression="set ApplicableControls = :a, NonApplicableControls = :n, #status = :s",
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':a': applicable_controls,
                ':n': non_applicable_controls,
                ':s': 'COMPLETED'
            }
        )
        logger.info(f"Successfully updated DynamoDB for service {service_name}")
        return True
    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e}")
        return False

def process_s3_file(service_name, output_location):
    """Process a file directly from S3"""
    try:
        logger.info(f"Processing S3 file for {service_name}: {output_location}")
        
        # Get the file content
        file_response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=output_location)
        content = file_response['Body'].read().decode('utf-8')
        
        # Parse the response
        parsed_response = parse_bedrock_response(content)
        
        # Update DynamoDB
        applicable_controls = parsed_response.get('applicable_controls', [])
        non_applicable_controls = parsed_response.get('non_applicable_controls', [])
        
        logger.info(f"Found {len(applicable_controls)} applicable controls and {len(non_applicable_controls)} non-applicable controls for {service_name}")
        
        update_result = update_dynamodb(service_name, applicable_controls, non_applicable_controls)
        
        return update_result
    except Exception as e:
        logger.error(f"Error processing S3 file {output_location}: {e}")
        return False

def process_completed_job(job_id, service_name, output_s3_prefix):
    """Process a completed Bedrock job"""
    try:
        # List objects in the output prefix
        response = s3.list_objects_v2(
            Bucket=PROMPTS_BUCKET,
            Prefix=output_s3_prefix
        )
        
        if 'Contents' not in response or len(response['Contents']) == 0:
            logger.error(f"No output files found for job {job_id}")
            return False
        
        # Get the latest output file
        output_files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        output_key = output_files[0]['Key']
        
        # Get the file content
        file_response = s3.get_object(Bucket=PROMPTS_BUCKET, Key=output_key)
        content = file_response['Body'].read().decode('utf-8')
        
        # Parse the response
        parsed_response = parse_bedrock_response(content)
        
        # Update DynamoDB
        applicable_controls = parsed_response.get('applicable_controls', [])
        non_applicable_controls = parsed_response.get('non_applicable_controls', [])
        
        logger.info(f"Found {len(applicable_controls)} applicable controls and {len(non_applicable_controls)} non-applicable controls for {service_name}")
        
        update_result = update_dynamodb(service_name, applicable_controls, non_applicable_controls)
        
        return update_result
    except Exception as e:
        logger.error(f"Error processing completed job {job_id}: {e}")
        return False

def lambda_handler(event, context):
    """Lambda handler function to check Bedrock job status"""
    try:
        # Scan DynamoDB for processing jobs
        table = dynamodb.Table(TABLE_NAME)
        
        # Get all items without filtering
        logger.info(f"Scanning table {TABLE_NAME} for jobs")
        response = table.scan()
        
        all_jobs = response.get('Items', [])
        # Filter jobs in PROCESSING state manually
        processing_jobs = [job for job in all_jobs if job.get('Status') == 'PROCESSING']
        logger.info(f"Found {len(processing_jobs)} jobs in PROCESSING state out of {len(all_jobs)} total jobs")
        
        for job in processing_jobs:
            service_name = job.get('ServiceName')
            job_id = job.get('JobId')
            output_location = job.get('OutputLocation')
            output_s3_prefix = job.get('OutputS3Prefix')
            
            logger.info(f"Processing job for service {service_name}")
            logger.info(f"Job data: JobId={job_id}, OutputLocation={output_location}, OutputS3Prefix={output_s3_prefix}")
            
            # If we have a direct output location, process it
            if output_location:
                logger.info(f"Processing using OutputLocation for {service_name}")
                process_s3_file(service_name, output_location)
                continue
                
            # If we have a job ID, check its status
            if job_id:
                try:
                    job_response = bedrock.get_model_invocation_job(jobId=job_id)
                    status = job_response.get('status')
                    
                    logger.info(f"Job {job_id} for service {service_name} has status: {status}")
                    
                    if status == 'COMPLETED':
                        logger.info(f"Processing completed job {job_id} for service {service_name}")
                        if output_s3_prefix:
                            process_completed_job(job_id, service_name, output_s3_prefix)
                        else:
                            logger.warning(f"No OutputS3Prefix found for job {job_id}")
                    elif status == 'FAILED':
                        logger.error(f"Job {job_id} for service {service_name} failed: {job_response.get('failureReason')}")
                        # Update DynamoDB with failure status
                        table.update_item(
                            Key={'ServiceName': service_name},
                            UpdateExpression="set #status = :s, FailureReason = :f",
                            ExpressionAttributeNames={
                                '#status': 'Status'
                            },
                            ExpressionAttributeValues={
                                ':s': 'FAILED',
                                ':f': job_response.get('failureReason', 'Unknown failure')
                            }
                        )
                except ClientError as e:
                    if 'AccessDeniedException' in str(e) or 'ResourceNotFoundException' in str(e):
                        logger.warning(f"Cannot access job {job_id}, trying to process output directly")
                        if output_location:
                            process_s3_file(service_name, output_location)
                    else:
                        logger.error(f"Error checking job {job_id} status: {e}")
                except Exception as e:
                    logger.error(f"Error checking job {job_id} status: {e}")
            else:
                logger.warning(f"No job ID found for service {service_name}")
                # Try to process using OutputLocation if available
                if output_location:
                    logger.info(f"Trying to process using OutputLocation for {service_name}")
                    process_s3_file(service_name, output_location)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f"Checked {len(processing_jobs)} jobs"})
        }
    except Exception as e:
        logger.error(f"Error checking Bedrock jobs: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }