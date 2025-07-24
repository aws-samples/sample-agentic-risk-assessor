import json
import boto3
import os
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    """Mark a session as inactive in DynamoDB"""
    try:
        # Handle OPTIONS requests
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'accept,authorization,content-type,origin,x-amz-date,x-amz-security-token,x-api-key',
                    'Access-Control-Allow-Methods': 'DELETE,OPTIONS'
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
        
        # Get session_id from path parameters
        session_id = event.get('pathParameters', {}).get('session_id')
        if not session_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'session_id is required'})
            }
        
        # Get DynamoDB table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'Sessions'))
        
        # Query all items for this session
        response = table.query(
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        
        items = response.get('Items', [])
        if not items:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Session not found'})
            }
        
        # Verify user owns this session
        user_owns_session = any(item.get('user_id') == user_id for item in items)
        if not user_owns_session:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Access denied'})
            }
        
        # Mark all items in this session as inactive
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(
                    Item={
                        **item,
                        'IsActive': False
                    }
                )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'message': 'Session deleted successfully'})
        }
        
    except Exception as e:
        print(f"Error deleting session: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }