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
        node_id = body.get('node_id')
        field = body.get('field')
        value = body.get('value')
        
        logger.info(f"Update node request: project_id={project_id}, node_id={node_id}, field={field}, value={value}") # nosemgrep: python.aws-lambda.security.tainted-sql-string.tainted-sql-string
        
        if not all([project_id, node_id, field, value]):
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
                    'message': 'project_id, node_id, field, and value are required'
                })
            }
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        
        # Update node in diagram analysis table
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
        nodes = item.get('nodes', [])
        
        # Find and update the node
        node_found = False
        for node in nodes:
            if node.get('id') == node_id:
                node[field] = value
                node_found = True
                logger.info(f"Updated node {node_id}: {field} = {value}")
                break
        
        if not node_found:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Node not found',
                    'message': f'Node {node_id} not found in project {project_id}'
                })
            }
        
        # Update the diagram analysis
        item['nodes'] = nodes
        item['updated_at'] = datetime.now().isoformat()
        diagram_table.put_item(Item=item)
        
        # Also update node controls table if it exists
        try:
            node_controls_table = dynamodb.Table(os.environ['NODE_CONTROLS_TABLE'])
            node_controls_response = node_controls_table.get_item(
                Key={'project_id': project_id, 'node_id': node_id}
            )
            
            if 'Item' in node_controls_response:
                node_item = node_controls_response['Item']
                # Map field names to node controls table schema
                field_mapping = {
                    'name': 'node_name',
                    'type': 'node_type', 
                    'description': 'node_description'
                }
                
                mapped_field = field_mapping.get(field, field)
                node_item[mapped_field] = value
                node_controls_table.put_item(Item=node_item)
                logger.info(f"Also updated node controls table: {mapped_field} = {value}")
        except Exception as e:
            logger.warning(f"Could not update node controls table: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'message': f'Successfully updated node {node_id}',
                'updated_field': field,
                'new_value': value,
                'refresh_required': True
            })
        }
        
    except Exception as e:
        logger.error(f"Error updating node: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to update node',
                'message': str(e)
            })
        }