import json
import uuid
import os
from datetime import datetime

def lambda_handler(event, context):
    """Create a new unique session ID"""
    try:
        # Handle OPTIONS requests
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'accept,authorization,content-type,origin,x-amz-date,x-amz-security-token,x-api-key',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({})
            }
        
        # Extract user_id from JWT token
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
        if not user_id:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        project_id = body.get('project_id')
        agent_id = body.get('agent_id')
        
        if not project_id or not agent_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'project_id and agent_id are required'})
            }
        
        # Generate unique session ID using UUID4 for maximum randomness
        session_id = str(uuid.uuid4())
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'session_id': session_id,
                'project_id': project_id,
                'agent_id': agent_id,
                'user_id': user_id,
                'created_at': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }