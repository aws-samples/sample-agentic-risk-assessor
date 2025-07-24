import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': ''
            }
        
        # Parse request
        body_str = event.get('body')
        if not body_str:
            raise ValueError("Request body is empty")
            
        body = json.loads(body_str)
        project_id = body.get('project_id')
        nodes = body.get('nodes', [])
        framework = body.get('framework')
        
        logger.info(f"Processing project_id: {project_id}, nodes count: {len(nodes)}, framework: {framework}")
        
        if not project_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'error': 'project_id is required'})
            }
            
        if not nodes:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'error': 'nodes array is required and cannot be empty'})
            }
        
        if not framework:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'error': 'Framework selection is required'})
            }
        
        # Initialize Step Functions client
        stepfunctions = boto3.client('stepfunctions')
        
        # Get Step Function ARN from environment
        step_function_arn = os.environ['STEP_FUNCTION_ARN']
        
        # Prepare input for Step Function
        step_function_input = {
            'project_id': project_id,
            'nodes': nodes,
            'framework': framework
        }
        
        # Start Step Function execution
        execution_name = f"map-controls-{project_id}-{int(datetime.utcnow().timestamp())}"
        
        response = stepfunctions.start_execution(
            stateMachineArn=step_function_arn,
            name=execution_name,
            input=json.dumps(step_function_input)
        )
        
        logger.info(f"Started Step Function execution: {response['executionArn']}")
        
        return {
            'statusCode': 202,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'message': 'Control mapping started',
                'project_id': project_id,
                'framework': framework,
                'execution_arn': response['executionArn'],
                'execution_name': execution_name,
                'total_nodes': len(nodes),
                'status': 'processing'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in map_controls: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'error': str(e)})
        }