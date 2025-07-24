import json
import os
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """
    Handler for admin/execution-status/{execution_arn} endpoint
    Gets the status of a Step Functions execution
    """
    try:
        # Get execution ARN from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'execution_arn' not in path_parameters:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({'error': 'Missing execution_arn parameter'})
            }
        
        execution_arn = path_parameters['execution_arn']
        
        # Initialize Step Functions client
        sfn = boto3.client('stepfunctions')
        
        # Get execution status
        response = sfn.describe_execution(
            executionArn=execution_arn
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'status': response['status'],
                'startDate': response['startDate'].isoformat(),
                'stopDate': response.get('stopDate', '').isoformat() if 'stopDate' in response else None
            })
        }
    except ClientError as e:
        print(f"Error getting execution status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': f"Error getting execution status: {str(e)}"})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': f"Unexpected error: {str(e)}"})
        }