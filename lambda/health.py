import json

def handler(event, context):
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET'
    }
    
    # Handle OPTIONS request (CORS preflight)
    if event['requestContext']['http']['method'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({})
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'Backend is healthy'})
    }