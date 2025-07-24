import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

def lambda_handler(event, context):
    """
    Handler for managing AWS services in DynamoDB
    Supports GET (list services) and POST (add service)
    """
    try:
        http_method = event.get('httpMethod', 'GET')
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        services_table = dynamodb.Table(os.environ.get('DYNAMODB_SERVICES_TABLE', 'risk-agent-services'))
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
        elif http_method == 'GET':
            return get_services(services_table)
        elif http_method == 'POST':
            return add_service(services_table, event)
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': f"Unexpected error: {str(e)}"})
        }

def get_services(services_table):
    """Get all services from DynamoDB"""
    try:
        response = services_table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={':status': 'ACTIVE'}
        )
        
        services = response.get('Items', [])
        
        # Sort services by name
        services.sort(key=lambda x: x.get('ServiceName', ''))
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'services': services})
        }
        
    except ClientError as e:
        print(f"Error retrieving services: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': f"Error retrieving services: {str(e)}"})
        }

def add_service(services_table, event):
    """Add a new service to DynamoDB"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
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
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'error': 'Service name is required'})
            }
        
        # Check if service already exists
        try:
            existing = services_table.get_item(Key={'ServiceName': service_name})
            if 'Item' in existing:
                return {
                    'statusCode': 409,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': json.dumps({'error': f'Service {service_name} already exists'})
                }
        except ClientError:
            pass  # Service doesn't exist, which is what we want
        
        # Add new service
        item = {
            'ServiceName': service_name,
            'Description': description or f"AWS {service_name} service",
            'IsNativeAws': is_native_aws,
            'CreatedAt': datetime.utcnow().isoformat(),
            'Status': 'ACTIVE'
        }
        
        if documentation_link:
            item['DocumentationLink'] = documentation_link
        
        services_table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'message': f'Service {service_name} added successfully', 'service': item})
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except ClientError as e:
        print(f"Error adding service: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': f"Error adding service: {str(e)}"})
        }