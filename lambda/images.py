import json
import boto3
import os

s3 = boto3.client('s3')

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
    
    # Get HTTP method from event
    http_method = event['requestContext']['http']['method']
    
    if http_method == 'GET':
        # Get image from S3
        path_params = event.get('pathParameters', {}) or {}
        if path_params and 'filename' in path_params:
            try:
                filename = path_params['filename']
                s3_bucket = os.environ['IMAGES_BUCKET']
                
                # Generate a pre-signed URL for the image
                presigned_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': s3_bucket, 'Key': filename},
                    ExpiresIn=3600  # 1 hour in seconds
                )
                
                # Redirect to the pre-signed URL
                return {
                    'statusCode': 302,
                    'headers': {
                        **headers,
                        'Location': presigned_url
                    },
                    'body': ''
                }
            except Exception as e:
                print(f"Error generating pre-signed URL: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'message': 'Error retrieving image'})
                }
        
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'message': 'Missing filename parameter'})
        }
    
    # Default response for unsupported methods
    return {
        'statusCode': 405,
        'headers': headers,
        'body': json.dumps({'message': 'Method not allowed'})
    }