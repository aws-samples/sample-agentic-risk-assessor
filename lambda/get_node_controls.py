import json
import boto3
import os
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Extract project_id from path parameters
        project_id = event['pathParameters']['id']
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ['NODE_CONTROLS_TABLE']
        table = dynamodb.Table(table_name)
        
        # Query node controls for the project
        response = table.query(
            KeyConditionExpression=Key('project_id').eq(project_id)
        )
        
        # Get latest version of each node (highest mapped_at timestamp)
        node_controls_dict = {}
        for item in response['Items']:
            node_id = item['node_id']
            mapped_at = item.get('mapped_at', '1970-01-01T00:00:00Z')
            
            # Keep only the latest version of each node
            if node_id not in node_controls_dict or mapped_at > node_controls_dict[node_id].get('mapped_at', '1970-01-01T00:00:00Z'):
                node_controls_dict[node_id] = {
                    'node_id': item['node_id'],
                    'node_name': item.get('node_name', 'N/A'),
                    'node_type': item.get('node_type', 'N/A'),
                    'mapped_controls': item.get('mapped_controls', []),
                    'mapped_at': mapped_at,
                    'status': item.get('status', 'unknown')
                }
        
        # Convert to list
        node_controls = list(node_controls_dict.values())
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'node_controls': node_controls,
                'total_nodes': len(node_controls)
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting node controls: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to get node controls',
                'message': str(e)
            })
        }