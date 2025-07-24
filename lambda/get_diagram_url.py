import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
projects_table = dynamodb.Table(os.environ.get('PROJECTS_TABLE', 'Projects'))

def lambda_handler(event, context):
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET'
        }
        
        if event['requestContext']['http']['method'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({})}
        
        # Get project ID from path parameters
        path_params = event.get('pathParameters', {}) or {}
        if not path_params or 'id' not in path_params:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Project ID is required'})
            }
        
        project_id = path_params['id']
        
        # Get project from database
        project = projects_table.get_item(Key={'id': project_id}).get('Item')
        if not project:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Project not found'})
            }
        
        # Check if project has a diagram filename stored
        if 'diagram_filename' not in project:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'No diagram found for this project'})
            }
        
        # Get the diagram filename and generate presigned URL
        diagram_filename = project['diagram_filename']
        diagram_bucket = os.environ.get('DIAGRAMS_BUCKET')
        
        # Generate presigned URL for the diagram
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': diagram_bucket, 'Key': diagram_filename},
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'diagram_url': presigned_url})
        }
        
    except Exception as e:
        print(f"Error getting diagram URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get diagram URL'})
        }