import json
import os
import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handler for admin/add-service endpoint
    Adds a new service directly to DynamoDB
    """
    try:
        # Handle OPTIONS request for CORS (support both API Gateway v1 and v2)
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': ''
            }
        
        # Parse request body
        if 'body' in event and event['body']:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        service_name = body.get('serviceName', '').strip()
        description = body.get('description', '').strip()
        documentation_link = body.get('documentationLink', '').strip()
        is_native_aws = body.get('isNativeAws', True)
        
        if not service_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({'error': 'Service name is required'})
            }
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        services_table = dynamodb.Table(os.environ.get('DYNAMODB_SERVICES_TABLE', 'risk-agent-services'))
        
        # Check if service already exists
        try:
            response = services_table.get_item(Key={'ServiceName': service_name})
            if 'Item' in response:
                return {
                    'statusCode': 409,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'POST,OPTIONS'
                    },
                    'body': json.dumps({'error': f'Service "{service_name}" already exists'})
                }
        except ClientError as e:
            logger.error(f"Error checking existing service: {str(e)}")
        
        # Add new service to services table
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        services_table.put_item(
            Item={
                'ServiceName': service_name,
                'Description': description or f"AWS {service_name} service",
                'DocumentationLink': documentation_link,
                'IsNativeAws': is_native_aws,
                'CreatedAt': current_time,
                'Status': 'ACTIVE'
            }
        )
        
        logger.info(f"Added new service to DynamoDB: {service_name}")
        
        return {
            'statusCode': 201,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'message': f'Service "{service_name}" added successfully',
                'service': {
                    'name': service_name,
                    'description': description,
                    'documentation_link': documentation_link,
                    'is_native_aws': is_native_aws
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error adding service: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'error': f'Error adding service: {str(e)}'})
        }