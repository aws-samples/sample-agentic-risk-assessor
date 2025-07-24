import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Check if all services in the current batch have completed processing"""
    logger.info(f"=== LAMBDA FUNCTION STARTED === Event: {json.dumps(event)}")
    try:
        services = event.get('services', [])
        framework = event.get('framework')
        
        if not framework:
            logger.error('Framework is required')
            return {'error': 'Framework selection is required'}
        
        if not services:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No services provided'})
            }
        
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls')
        table = dynamodb.Table(table_name)
        
        completed_services = []
        failed_services = []
        processing_services = []
        
        for service in services:
            try:
                logger.info(f"Checking service: {service} with framework: {framework}")
                response = table.get_item(Key={
                    'ServiceName': service,
                    'Framework': framework
                })
                
                logger.info(f"DynamoDB response for {service}: {'Item found' if 'Item' in response else 'No item found'}")
                
                if 'Item' in response:
                    item = response['Item']
                    status = item.get('Status', 'UNKNOWN')
                    logger.info(f"Service {service} status: {status}")
                    
                    # Check if explicitly marked as completed or failed
                    if status in ['COMPLETED', 'COMPLETE']:
                        logger.info(f"Service {service} marked as complete with status: {status}")
                        completed_services.append(service)
                    elif status == 'FAILED':
                        failed_services.append(service)
                    else:
                        # For PROCESSING status, check if controls have been processed
                        applicable_controls = item.get('ApplicableControls', [])
                        processed_at = item.get('ProcessedAt')
                        
                        logger.info(f"Service {service} fallback check - ApplicableControls: {len(applicable_controls) if applicable_controls else 0}, ProcessedAt: {'present' if processed_at else 'missing'}")
                        
                        # Consider service complete if it has processed controls and a recent timestamp
                        if applicable_controls and processed_at:
                            logger.info(f"Service {service} has {len(applicable_controls)} processed controls")
                            completed_services.append(service)
                        else:
                            processing_services.append(service)
                else:
                    # No record exists yet
                    logger.info(f"No DynamoDB record found for service: {service}")
                    processing_services.append(service)
            except ClientError as e:
                logger.error(f"Error checking service {service}: {e}")
                processing_services.append(service)
        
        batch_status = "COMPLETE" if len(processing_services) == 0 else "PROCESSING"
        
        logger.info(f"Batch status: {batch_status}, Completed: {len(completed_services)}, Processing: {len(processing_services)}")
        
        return {
            'batchStatus': batch_status,
            'completedServices': completed_services,
            'failedServices': failed_services,
            'processingServices': processing_services,
            'totalServices': len(services),
            'completedCount': len(completed_services),
            'failedCount': len(failed_services),
            'processingCount': len(processing_services)
        }
        
    except Exception as e:
        logger.error(f"Error checking batch completion: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }