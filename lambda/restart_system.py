import json
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Log the region being used
        import os
        region = os.environ.get('AWS_REGION', 'us-east-1')
        logger.info(f"Using AWS region: {region}")
        
        ecs_client = boto3.client('ecs')
        cluster_name = 'risk-agent-agents'
        
        # Log cluster and services info
        logger.info(f"Attempting to restart services in cluster: {cluster_name}")
        
        # First, verify the cluster exists
        try:
            clusters_response = ecs_client.describe_clusters(clusters=[cluster_name])
            logger.info(f"Cluster info: {clusters_response}")
        except Exception as cluster_error:
            logger.error(f"Error describing cluster: {cluster_error}")
            
        # List all clusters to debug
        try:
            all_clusters = ecs_client.list_clusters()
            logger.info(f"All available clusters: {all_clusters}")
        except Exception as list_error:
            logger.error(f"Error listing clusters: {list_error}")
        
        # All 4 agent services to restart
        services = [
            'risk-agent-architect',
            'risk-agent-security_architect', 
            'risk-agent-risk_assessment',
            'risk-agent-auditor'
        ]
        
        results = {}
        
        for service in services:
            try:
                # Force new deployment
                response = ecs_client.update_service(
                    cluster=cluster_name,
                    service=service,
                    forceNewDeployment=True,
                    deploymentConfiguration={
                        'maximumPercent': 200,
                        'minimumHealthyPercent': 0
                    }
                )
                
                results[service] = {
                    'status': 'success',
                    'message': 'Restart initiated'
                }
                logger.info(f"Successfully initiated restart for {service}")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                results[service] = {
                    'status': 'error',
                    'message': f"{error_code}: {error_message}"
                }
                logger.error(f"Failed to restart {service}: {error_message}")
        
        # Check if any services failed
        failed_services = [svc for svc, result in results.items() if result['status'] == 'error']
        
        if failed_services:
            return {
                'statusCode': 207,  # Multi-status
                'headers': headers,
                'body': json.dumps({
                    'message': f'Partial success. Failed services: {", ".join(failed_services)}',
                    'results': results
                })
            }
        else:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': 'All agent services restart initiated successfully',
                    'results': results
                })
            }
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }