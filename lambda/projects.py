import json
import boto3
import uuid
import os
import base64
from datetime import datetime
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

def handler(event, context):
    # Define headers first to avoid UnboundLocalError
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
    }
    
    try:
        print(f"Event received: {json.dumps(event)}")
        
        # Check if environment variable exists
        projects_table_name = os.environ.get('PROJECTS_TABLE')
        if not projects_table_name:
            raise ValueError("PROJECTS_TABLE environment variable not set")
            
        table = dynamodb.Table(projects_table_name)
        
        if event['requestContext']['http']['method'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        http_method = event['requestContext']['http']['method']
        
        if http_method == 'GET':
            path_params = event.get('pathParameters', {}) or {}
            if path_params and 'id' in path_params:
                response = table.get_item(Key={'id': path_params['id']})
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(response.get('Item', {}), cls=DecimalEncoder)
                }
            else:
                response = table.scan()
                # Filter out organization profiles - they are not projects
                items = [item for item in response.get('Items', []) if item.get('type') != 'organization_profile']
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(items, cls=DecimalEncoder)
                }
        
        elif http_method == 'POST':
            body = json.loads(event['body'])
            project_id = str(uuid.uuid4())
            
            item = {
                'id': project_id,
                'name': body['name'],
                'description': body['description'],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if 'data_classification' in body:
                item['data_classification'] = body['data_classification']
            if 'availability' in body:
                item['availability'] = body['availability']
            if 'has_pii' in body:
                item['has_pii'] = body['has_pii']
            if 'regulations' in body and body['regulations']:
                item['regulations'] = body['regulations']
            if 'profile_id' in body:
                item['profile_id'] = body['profile_id']
            
            table.put_item(Item=item)
            
            return {
                'statusCode': 201,
                'headers': headers,
                'body': json.dumps({'message': 'Project created successfully', 'project_id': project_id})
            }
        
        elif http_method == 'PUT':
            path_params = event.get('pathParameters', {}) or {}
            if not path_params or 'id' not in path_params:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'message': 'Project ID is required'})
                }
            
            project_id = path_params['id']
            body = json.loads(event['body'])
            
            # Update the project
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.now().isoformat()}
            
            if 'name' in body:
                update_expression += ", #name = :name"
                expression_values[':name'] = body['name']
            if 'description' in body:
                update_expression += ", description = :description"
                expression_values[':description'] = body['description']
            if 'data_classification' in body:
                update_expression += ", data_classification = :data_classification"
                expression_values[':data_classification'] = body['data_classification']
            if 'availability' in body:
                update_expression += ", availability = :availability"
                expression_values[':availability'] = body['availability']
            if 'has_pii' in body:
                update_expression += ", has_pii = :has_pii"
                expression_values[':has_pii'] = body['has_pii']
            if 'regulations' in body:
                update_expression += ", regulations = :regulations"
                expression_values[':regulations'] = body['regulations']
            if 'profile_id' in body:
                update_expression += ", profile_id = :profile_id"
                expression_values[':profile_id'] = body['profile_id']
            
            table.update_item(
                Key={'id': project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={'#name': 'name'} if 'name' in body else None,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'Project updated successfully'})
            }
        
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'message': 'Method not allowed'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': f'Internal server error: {str(e)}'})
        }