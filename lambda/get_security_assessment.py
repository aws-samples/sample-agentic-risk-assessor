import json
import boto3
import os

def lambda_handler(event, context):
    """Get latest security assessment for a project"""
    try:
        project_id = event['pathParameters']['id']
        
        dynamodb = boto3.resource('dynamodb')
        s3_client = boto3.client('s3')
        
        table_name = os.environ.get('PROJECTS_TABLE', 'Projects')
        bucket_name = os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents')
        
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={'id': project_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Project not found'})
            }
        
        security_assessments = response['Item'].get('security_assessments', [])
        if not security_assessments:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No security assessment found'})
            }
        
        # Get latest assessment
        latest_assessment = security_assessments[-1]
        
        # Get content from S3
        s3_response = s3_client.get_object(
            Bucket=bucket_name,
            Key=latest_assessment['s3_key']
        )
        content = s3_response['Body'].read().decode('utf-8')
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'assessment': json.loads(content) if content.startswith('{') else {'content': content}
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }