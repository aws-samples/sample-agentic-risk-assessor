import json
import boto3
import logging
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Mark a service as complete after all control families are processed
    """
    try:
        logger.info(f"Marking service complete: {json.dumps(event)}")
        
        # Extract parameters
        service = event.get('service')
        framework = event.get('framework')
        
        if not all([service, framework]):
            raise ValueError("Missing required parameters: service, framework")
        
        # Mark service as complete
        mark_service_complete(service, framework)
        
        logger.info(f"Successfully marked service {service} as complete for {framework}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'service': service,
                'framework': framework,
                'status': 'COMPLETE',
                'completed_at': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error marking service complete: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'service': event.get('service', 'unknown'),
                'framework': event.get('framework', 'unknown')
            })
        }

def mark_service_complete(service, framework):
    """Mark service as complete in DynamoDB — works with both old and new storage formats"""
    
    table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls')
    table = dynamodb.Table(table_name)
    
    try:
        # Update or create the base service record (old format key)
        table.update_item(
            Key={
                'ServiceName': service,
                'Framework': framework
            },
            UpdateExpression='SET #status = :complete, CompletedAt = :timestamp',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':complete': 'COMPLETE',
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Marked service {service} as COMPLETE for {framework}")
        
    except Exception as e:
        logger.error(f"Failed to mark service complete: {str(e)}")
        raise
