import json
import boto3
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info(f"Processing node: {json.dumps(event)}")
        
        # Extract node information from Step Function input
        project_id = event['project_id']
        node = event['node']
        
        node_id = node['id']
        node_type = node.get('type', '')
        node_name = node.get('name', '')
        node_description = node.get('description', '')
        
        # Initialize AWS clients
        dynamodb = boto3.resource('dynamodb')
        
        # Get configuration
        node_controls_table_name = os.environ['NODE_CONTROLS_TABLE']
        service_controls_table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'service-controls')
        
        node_controls_table = dynamodb.Table(node_controls_table_name)
        service_controls_table = dynamodb.Table(service_controls_table_name)
        
        # Get framework from event
        framework = event.get('framework')
        
        if not framework:
            logger.error("No framework provided in the event")
            return {
                'statusCode': 400,
                'node_id': node_id,
                'status': 'failed',
                'error': 'Framework selection is required'
            }
        
        # Map node type to AWS service name
        service_mapping = {
            'EC2': 'EC2',
            'RDS': 'RDS',
            'S3': 'S3',
            'Lambda': 'Lambda',
            'VPC': 'VPC',
            'ELB': 'Elastic Load Balancing',
            'ALB': 'Elastic Load Balancing',
            'NLB': 'Elastic Load Balancing',
            'CloudFront': 'CloudFront',
            'Route53': 'Route 53',
            'IAM': 'IAM',
            'KMS': 'KMS',
            'CloudWatch': 'CloudWatch',
            'CloudTrail': 'CloudTrail',
            'Config': 'Config',
            'GuardDuty': 'GuardDuty',
            'SecurityHub': 'Security Hub',
            'WAF': 'WAF',
            'Shield': 'Shield',
            'Inspector': 'Inspector',
            'Macie': 'Macie',
            'Secrets Manager': 'Secrets Manager',
            'Systems Manager': 'Systems Manager',
            'ECS': 'ECS',
            'EKS': 'EKS',
            'Fargate': 'Fargate',
            'API Gateway': 'API Gateway',
            'Cognito': 'Cognito',
            'SQS': 'SQS',
            'SNS': 'SNS',
            'EventBridge': 'EventBridge',
            'Step Functions': 'Step Functions',
            'DynamoDB': 'DynamoDB',
            'ElastiCache': 'ElastiCache',
            'Redshift': 'Redshift',
            'EMR': 'EMR',
            'Glue': 'Glue',
            'Athena': 'Athena',
            'QuickSight': 'QuickSight'
        }
        
        try:
            # Get the service name for this node type
            service_name = service_mapping.get(node_type, node_type)
            logger.info(f"Mapping node type '{node_type}' to service '{service_name}' for framework '{framework}'")
            
            # Query service controls table for this service and framework
            try:
                response = service_controls_table.get_item(
                    Key={
                        'ServiceName': service_name,
                        'Framework': framework
                    }
                )
                
                if 'Item' in response:
                    service_item = response['Item']
                    controls = service_item.get('ApplicableControls', [])
                    logger.info(f"Found {len(controls)} controls for service '{service_name}' with framework '{framework}'")
                else:
                    logger.warning(f"No controls found for service '{service_name}' with framework '{framework}'. Using fallback.")
                    # Fallback to basic access control
                    controls = [{
                        "control_id": "AC-6",
                        "control_name": "Least Privilege",
                        "category": "Identity & Access Management",
                        "priority": "Baseline",
                        "rationale": f"Access control is essential for {node_type} security"
                    }]
                    
            except Exception as e:
                logger.error(f"Error querying service controls: {str(e)}")
                # Fallback controls
                controls = [{
                    "control_id": "AC-6",
                    "control_name": "Least Privilege",
                    "category": "Identity & Access Management",
                    "priority": "Baseline",
                    "rationale": f"Access control is essential for {node_type} security"
                }]
            
            logger.info(f"DynamoDB lookup completed. Total controls: {len(controls)}")
            
            # Save mapping to DynamoDB
            mapping_item = {
                'node_id': node_id,
                'project_id': project_id,
                'node_type': node_type,
                'node_name': node_name,
                'node_description': node_description,
                'mapped_controls': controls,
                'mapped_at': datetime.utcnow().isoformat(),
                'mapping_source': 'dynamodb_lookup',
                'framework': framework,
                'status': 'completed',
                'controls_extracted': len(controls),
                'service_name': service_name
            }
            
            node_controls_table.put_item(Item=mapping_item)
            
            return {
                'statusCode': 200,
                'node_id': node_id,
                'controls_count': len(controls),
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {str(e)}")
            
            # Use fallback control for any errors
            fallback_controls = [{
                "control_id": "AC-6",
                "control_name": "Least Privilege",
                "category": "Identity & Access Management",
                "priority": "Baseline",
                "rationale": f"Access control is essential for {node_type} security"
            }]
            
            # Save error mapping to DynamoDB
            error_mapping_item = {
                'node_id': node_id,
                'project_id': project_id,
                'node_type': node_type,
                'node_name': node_name,
                'node_description': node_description,
                'mapped_controls': fallback_controls,
                'mapped_at': datetime.utcnow().isoformat(),
                'mapping_source': 'error_fallback',
                'framework': framework,
                'status': 'error',
                'error_message': str(e),
                'used_fallback': True
            }
            
            node_controls_table.put_item(Item=error_mapping_item)
            
            return {
                'statusCode': 500,
                'node_id': node_id,
                'controls_count': len(fallback_controls),
                'status': 'error',
                'error': str(e)
            }
            
    except Exception as e:
        logger.error(f"Critical error in process_node_controls: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'critical_error',
            'error': str(e)
        }