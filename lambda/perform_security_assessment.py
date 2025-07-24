import json
import boto3
import os
from datetime import datetime

BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')

def lambda_handler(event, context):
    """Perform comprehensive security assessment based on document and responses"""
    try:
        print(f"Lambda input event: {json.dumps(event, indent=2)}")
        
        # Parse input
        project_id = event['pathParameters']['id']
        
        # Get project document
        lambda_client = boto3.client('lambda')
        project_response = lambda_client.invoke(
            FunctionName='risk-agent-projects-api',
            Payload=json.dumps({
                'requestContext': {'http': {'method': 'GET'}},
                'pathParameters': {'id': project_id}
            })
        )
        project_result = json.loads(project_response['Payload'].read())
        if 'body' in project_result:
            project_data = json.loads(project_result['body']) if isinstance(project_result['body'], str) else project_result['body']
        else:
            project_data = project_result
        
        # Get document content
        document_content = 'No document available'
        if project_data.get('document_key'):
            doc_response = lambda_client.invoke(
                FunctionName='get-document-content',
                Payload=json.dumps({
                    'requestContext': {'http': {'method': 'GET'}},
                    'pathParameters': {'id': project_id}
                })
            )
            doc_result = json.loads(doc_response['Payload'].read())
            if 'body' in doc_result:
                doc_body = json.loads(doc_result['body']) if isinstance(doc_result['body'], str) else doc_result['body']
                document_content = doc_body.get('content', 'No document content available')
            else:
                document_content = doc_result.get('content', 'No document content available')
        
        # Get security responses
        dynamodb = boto3.resource('dynamodb')
        responses_table = dynamodb.Table(os.environ.get('SECURITY_RESPONSES_TABLE', 'risk-agent-security-responses'))
        
        responses_response = responses_table.get_item(
            Key={'project_id': project_id}
        )
        
        security_responses = []
        if 'Item' in responses_response:
            security_responses = responses_response['Item'].get('responses', [])
        
        print(f"Found {len(security_responses)} security responses")
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime')
        
        # Load assessment prompt from S3
        s3_client = boto3.client('s3')
        app_data_bucket = os.environ.get('APP_DATA_BUCKET')
        response = s3_client.get_object(
            Bucket=app_data_bucket,
            Key='system_prompts/security_architect/security_assessment.txt'
        )
        prompt_template = response['Body'].read().decode('utf-8')
        
        # Format prompt
        prompt = prompt_template.format(
            project_id=project_id,
            document_content=document_content,
            security_responses=json.dumps(security_responses, indent=2)
        )
        
        print(f"Calling Bedrock for security assessment...")
        
        # Call Bedrock for assessment
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 4000,
                'temperature': 0.0,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        bedrock_text = result['content'][0]['text']
        
        # Strip markdown code blocks if present
        if bedrock_text.strip().startswith('```'):
            lines = bedrock_text.strip().split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            bedrock_text = '\n'.join(lines).strip()
        
        assessment = json.loads(bedrock_text)
        
        # Add metadata
        assessment['metadata'] = {
            'project_id': project_id,
            'assessment_date': datetime.utcnow().isoformat(),
            'version': '1.0',
            'assessment_type': 'comprehensive_security'
        }
        
        # Store assessment in DynamoDB
        assessments_table = dynamodb.Table(os.environ.get('SECURITY_ASSESSMENTS_TABLE', 'risk-agent-security-assessments'))
        
        assessments_table.put_item(
            Item={
                'project_id': project_id,
                'assessment': assessment,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0',
                'status': 'completed'
            }
        )
        
        # Also save to S3 for detailed storage
        assessment_key = f'security_assessments/{project_id}/assessment_v1.0.json'
        s3_client.put_object(
            Bucket=app_data_bucket,
            Key=assessment_key,
            Body=json.dumps(assessment, indent=2),
            ContentType='application/json'
        )
        
        print(f"Security assessment completed and saved")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'assessment': assessment,
                's3_key': assessment_key
            })
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }