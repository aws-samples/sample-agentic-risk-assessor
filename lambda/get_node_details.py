import json
import boto3
import os
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Extract project_id and node_id from path parameters
        path_params = event.get('pathParameters', {})
        project_id = path_params.get('projectId') or path_params.get('id')
        node_id = path_params.get('nodeId')
        
        logger.info(f"Extracted parameters: project_id={project_id}, node_id={node_id}")
        
        if not project_id or not node_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': json.dumps({
                    'error': 'Missing parameters',
                    'message': 'Both project_id and node_id are required'
                })
            }
        
        logger.info(f"Getting node details for project: {project_id}, node: {node_id}")
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ['NODE_CONTROLS_TABLE']
        table = dynamodb.Table(table_name)
        
        # Get the specific node details
        response = table.get_item(
            Key={
                'project_id': project_id,
                'node_id': node_id
            }
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': json.dumps({
                    'error': 'Node not found',
                    'message': f'Node {node_id} not found in project {project_id}'
                })
            }
        
        item = response['Item']
        
        # Format the response with all node details
        node_details = {
            'node_id': item['node_id'],
            'node_name': item.get('node_name', ''),
            'node_type': item.get('node_type', ''),
            'node_description': item.get('node_description', ''),
            'project_id': item['project_id'],
            'mapped_controls': item.get('mapped_controls', []),
            'mapped_at': item.get('mapped_at', ''),
            'mapping_source': item.get('mapping_source', 'bedrock'),
            'status': item.get('status', 'unknown')
        }
        
        logger.info(f"Found node details: {node_details['node_name']} with {len(node_details['mapped_controls'])} controls")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps(node_details)
        }
        
    except Exception as e:
        logger.error(f"Error getting node details: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to get node details',
                'message': str(e)
            })
        }