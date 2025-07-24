import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3', region_name='us-east-1')
APP_BUCKET = os.environ.get('APP_DATA_BUCKET', 'risk-agent-app-data-a57fe9d3')


def lambda_handler(event, context):
    """Serve a generated control reference HTML page from S3."""
    try:
        framework = event.get('pathParameters', {}).get('framework', '')
        service = event.get('pathParameters', {}).get('service', '')

        if not framework or not service:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing framework or service'})
            }

        key = f"control-references/{framework}/{service}.html"
        logger.info(f"Serving reference: s3://{APP_BUCKET}/{key}")

        obj = s3.get_object(Bucket=APP_BUCKET, Key=key)
        html = obj['Body'].read().decode('utf-8')

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': html
        }

    except s3.exceptions.NoSuchKey:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Reference not generated yet. Run control mapping first.'})
        }
    except Exception as e:
        logger.error(f"Error serving reference: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
