import json
import boto3
import uuid
import base64
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        }
        
        method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        if method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        body = json.loads(event['body'])
        project_id = body.get('project_id')
        image_data = body.get('image_data')  # base64 encoded
        image_type = body.get('image_type', 'image/png')
        
        if not project_id or not image_data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'project_id and image_data are required'})
            }
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[-1])
        
        # Generate unique filename
        diagram_filename = f"{uuid.uuid4().hex}.png"
        
        # Upload to S3 images bucket
        s3.put_object(
            Bucket=os.environ.get('IMAGES_BUCKET'),
            Key=diagram_filename,
            Body=image_bytes,
            ContentType=image_type
        )
        
        # Update project with diagram_filename
        projects_table = dynamodb.Table('Projects')
        projects_table.update_item(
            Key={'id': project_id},
            UpdateExpression="SET diagram_filename = :df, updated_at = :ua",
            ExpressionAttributeValues={
                ':df': diagram_filename,
                ':ua': datetime.now().isoformat()
            }
        )
        
        # Return diagram URL
        diagram_url = f"{os.environ.get('API_GATEWAY_URL', '')}/api/images/{diagram_filename}"
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Image uploaded successfully',
                'diagram_filename': diagram_filename,
                'diagram_url': diagram_url
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to upload image: {str(e)}'})
        }