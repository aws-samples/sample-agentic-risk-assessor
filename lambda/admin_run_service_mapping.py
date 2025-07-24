import json
import os
import boto3
from botocore.exceptions import ClientError
import traceback
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handler for admin/run-service-mapping endpoint
    Starts the Step Functions execution for a specific service
    """
    try:
        logger.info("=== ADMIN RUN SERVICE MAPPING START ===")
        logger.info(f"Full event: {json.dumps(event, default=str)}")
        logger.info(f"Context: {vars(context)}")
        
        # Check environment variables
        step_functions_arn = os.environ.get('SERVICE_CONTROLS_STEP_FUNCTION_ARN')
        logger.info(f"Environment - SERVICE_CONTROLS_STEP_FUNCTION_ARN: {step_functions_arn}")
        
        # Handle OPTIONS request for CORS - Check multiple possible locations
        http_method = event.get('httpMethod')
        if not http_method:
            http_method = event.get('requestContext', {}).get('http', {}).get('method')
        
        # Also check routeKey for API Gateway v2
        route_key = event.get('routeKey', '')
        is_options = (http_method == 'OPTIONS' or route_key.startswith('OPTIONS '))
        
        logger.info(f"HTTP method: {http_method}, Route key: {route_key}, Is OPTIONS: {is_options}")
        
        if is_options:
            logger.info("Handling OPTIONS preflight request")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
            
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError as e:
                print(f"Error parsing request body: {str(e)}")
                print(f"Raw body: {event.get('body')}")
                
        service_name = body.get('service')
        framework = body.get('framework')
        
        logger.info(f"Parsed service: {service_name}")
        logger.info(f"Parsed framework: {framework}")
        logger.info(f"Request body: {body}")
        
        if not framework:
            error_msg = 'Framework selection is required'
            logger.error(f"Framework validation failed: {error_msg}")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({'error': error_msg})
            }
        
        if not service_name:
            error_msg = 'Service name is required'
            logger.error(f"Service validation failed: {error_msg}")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({'error': error_msg})
            }
        
        # Initialize Step Functions client
        sfn = boto3.client('stepfunctions')
        
        # Validate Step Functions ARN
        if not step_functions_arn:
            error_msg = "SERVICE_CONTROLS_STEP_FUNCTION_ARN environment variable is not set"
            logger.error(error_msg)
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({'error': error_msg})
            }
            
        logger.info(f"Using Step Functions ARN: {step_functions_arn}")
        
        # Start execution with input containing the specified service and framework
        input_data = {
            "services": [service_name],
            "framework": framework
        }
        logger.info(f"Step Functions input: {json.dumps(input_data)}")
        
        logger.info("Starting Step Functions execution")
        response = sfn.start_execution(
            stateMachineArn=step_functions_arn,
            input=json.dumps(input_data)
        )
        
        logger.info(f"Step Functions response: {json.dumps(response, default=str)}")
        logger.info(f"Execution started: {response['executionArn']}")
        
        success_response = {
            'executionArn': response['executionArn'],
            'startDate': response['startDate'].isoformat()
        }
        logger.info(f"Success response: {json.dumps(success_response, default=str)}")
        logger.info("=== ADMIN RUN SERVICE MAPPING SUCCESS ===")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps(success_response)
        }
    except ClientError as e:
        error_message = str(e)
        logger.error(f"AWS ClientError starting Step Functions execution: {error_message}")
        logger.error(f"Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
        logger.error(f"Error message: {e.response.get('Error', {}).get('Message', 'Unknown')}")
        
        # Check for specific error types
        if "AccessDeniedException" in error_message:
            logger.error("Access denied - check IAM permissions for the Lambda function")
        elif "ValidationException" in error_message:
            logger.error("Validation error - check the Step Functions ARN and input format")
        elif "StateMachineDoesNotExist" in error_message:
            logger.error("State machine does not exist - check the ARN is correct")
        
        logger.error("=== ADMIN RUN SERVICE MAPPING CLIENT ERROR ===")
            
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'error': f"Error starting Step Functions execution: {error_message}"})
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error: {error_message}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error("=== ADMIN RUN SERVICE MAPPING UNEXPECTED ERROR ===")
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'error': f"Unexpected error: {error_message}"})
        }