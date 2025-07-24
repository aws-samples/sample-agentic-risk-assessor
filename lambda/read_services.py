import json
import os
import boto3
import logging
import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Read AWS services configuration and set appropriate services to QUEUED status"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls'))
        
        # Get framework from event (passed from admin_run_mapping)
        logger.info(f"Full event received: {json.dumps(event, default=str)}")
        framework = event.get('framework')
        logger.info(f"Extracted framework: {framework}")
        logger.info(f"Framework type: {type(framework)}")
        
        if not framework:
            logger.error('Framework is required')
            return {'error': 'Framework selection is required'}
        
        # Check if specific services are provided in the event (individual processing)
        input_services = event.get('services', [])
        
        if input_services:
            # Individual service processing - only process specified services
            services_list = input_services
            logger.info(f"Processing specific services: {services_list}")
        else:
            # Bulk processing - load all services from DynamoDB services table
            try:
                services_table = dynamodb.Table(os.environ.get('DYNAMODB_SERVICES_TABLE', 'risk-agent-services'))
                response = services_table.scan(
                    FilterExpression='#status = :status',
                    ExpressionAttributeNames={'#status': 'Status'},
                    ExpressionAttributeValues={':status': 'ACTIVE'}
                )
                services_list = [item['ServiceName'] for item in response.get('Items', [])]
                logger.info(f"Loaded {len(services_list)} services from DynamoDB for bulk processing")
            except Exception as e:
                logger.error(f"Error loading services from DynamoDB, using default: {str(e)}")
                services_list = ["EC2", "S3", "RDS", "Lambda", "IAM"]
        
        # Set only the target services to QUEUED status for the specified framework
        current_time = datetime.datetime.now().isoformat()
        
        for service_name in services_list:
            try:
                table.update_item(
                    Key={
                        'ServiceName': service_name,
                        'Framework': framework
                    },
                    UpdateExpression='SET #status = :status, ProcessedAt = :timestamp',
                    ExpressionAttributeNames={'#status': 'Status'},
                    ExpressionAttributeValues={
                        ':status': 'QUEUED',
                        ':timestamp': current_time
                    }
                )
                logger.info(f"Set {service_name} ({framework}) status to QUEUED in DynamoDB")
            except ClientError as e:
                logger.error(f"Error updating status for {service_name} ({framework}): {e}")
                # Continue processing other services even if one fails
        
        return {
            'services': services_list,
            'framework': framework
        }
        
    except Exception as e:
        logger.error(f"Error in read_services: {str(e)}")
        raise