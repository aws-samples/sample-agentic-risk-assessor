import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Extract parameters
        body = json.loads(event.get('body', '{}'))
        project_id = body.get('project_id')
        flow_id = body.get('flow_id')
        field = body.get('field')
        value = body.get('value')
        
        logger.info(f"Update flow request: project_id={project_id}, flow_id={flow_id}, field={field}, value={value}") # nosemgrep: python.aws-lambda.security.tainted-sql-string.tainted-sql-string
        
        if not all([project_id, flow_id, field, value]):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': json.dumps({
                    'error': 'Missing parameters',
                    'message': 'project_id, flow_id, field, and value are required'
                })
            }
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        diagram_table = dynamodb.Table(os.environ['DIAGRAM_ANALYSIS_TABLE'])
        
        # Get current diagram analysis
        response = diagram_table.get_item(Key={'project_id': project_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Project not found',
                    'message': f'No diagram analysis found for project {project_id}'
                })
            }
        
        item = response['Item']
        flows = item.get('flows', [])
        
        # Find and update the flow
        flow_found = False
        for flow in flows:
            if flow.get('id') == flow_id:
                flow[field] = value
                flow_found = True
                logger.info(f"Updated flow {flow_id}: {field} = {value}")
                break
        
        if not flow_found:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Flow not found',
                    'message': f'Flow {flow_id} not found in project {project_id}'
                })
            }
        
        # Update the diagram analysis
        item['flows'] = flows
        item['updated_at'] = datetime.now().isoformat()
        diagram_table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'message': f'Successfully updated flow {flow_id}',
                'updated_field': field,
                'new_value': value,
                'refresh_required': True
            })
        }
        
    except Exception as e:
        logger.error(f"Error updating flow: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to update flow',
                'message': str(e)
            })
        }