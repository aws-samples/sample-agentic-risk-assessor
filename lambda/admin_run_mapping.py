import json
import os
import boto3
from botocore.exceptions import ClientError
import logging
import traceback
import sys

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add handler to ensure logs go to CloudWatch
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s'))
    logger.addHandler(handler)

def lambda_handler(event, context):
    """
    Handler for admin/run-mapping endpoint
    Starts the Step Functions execution for service controls mapping
    """
    logger.info("=== ADMIN RUN MAPPING START ===")
    logger.info(f"Lambda function name: {context.function_name}")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Remaining time: {context.get_remaining_time_in_millis()}ms")
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    try:
        # Log raw event details
        logger.info(f"Event type: {type(event)}")
        logger.info(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
        logger.info(f"Full event: {json.dumps(event, default=str, indent=2)}")
        
        # Log HTTP details if available
        if 'httpMethod' in event:
            logger.info(f"HTTP Method: {event['httpMethod']}")
        if 'path' in event:
            logger.info(f"Path: {event['path']}")
        
        # Handle OPTIONS request for CORS preflight
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        route_key = event.get('routeKey', '')
        logger.info(f"Detected HTTP method: {http_method}")
        logger.info(f"Route key: {route_key}")
        
        # Check for OPTIONS in multiple ways
        is_options = (http_method == 'OPTIONS' or route_key.startswith('OPTIONS '))
        logger.info(f"Is OPTIONS request: {is_options}")
        
        if is_options:
            logger.info("Handling OPTIONS preflight request")
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
        
        # Check environment variables
        step_functions_arn = os.environ.get('STEP_FUNCTIONS_ARN')
        app_bucket = os.environ.get('APP_BUCKET')
        logger.info(f"Environment - STEP_FUNCTIONS_ARN: {step_functions_arn}")
        logger.info(f"Environment - APP_BUCKET: {app_bucket}")
        
        # Parse request body to get framework
        raw_body = event.get('body')
        logger.info(f"Raw body: {raw_body}")
        logger.info(f"Body type: {type(raw_body)}")
        
        try:
            if raw_body:
                body = json.loads(raw_body)
                logger.info(f"Successfully parsed JSON body: {json.dumps(body, indent=2)}")
            else:
                body = {}
                logger.info("No body provided, using empty dict")
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error: {str(json_err)}")
            logger.error(f"Raw body that failed: {repr(raw_body)}")
            raise
        
        framework = body.get('framework')
        logger.info(f"Extracted framework: {framework}")
        
        # Validate framework - reject 'all' and empty values
        if not framework or framework == 'all':
            error_msg = 'Please select a specific framework. The "All Frameworks" option is only for viewing existing results.'
            logger.error(f"Framework validation failed: {error_msg}")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': error_msg})
            }
        
        # Validate Step Functions ARN
        if not step_functions_arn:
            error_msg = "STEP_FUNCTIONS_ARN environment variable is not set"
            logger.error(error_msg)
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': error_msg})
            }
        
        # Initialize Step Functions client
        logger.info("Initializing Step Functions client")
        try:
            sfn = boto3.client('stepfunctions')
            logger.info("Step Functions client initialized successfully")
        except Exception as boto_err:
            logger.error(f"Failed to initialize Step Functions client: {str(boto_err)}")
            raise
        
        # Prepare execution input
        execution_input = {'framework': framework}
        execution_input_json = json.dumps(execution_input)
        logger.info(f"Step Functions input: {execution_input_json}")
        
        # Start execution with framework information
        logger.info(f"Starting Step Functions execution with ARN: {step_functions_arn}")
        
        try:
            response = sfn.start_execution(
                stateMachineArn=step_functions_arn,
                input=execution_input_json
            )
            logger.info(f"Step Functions execution started successfully")
            logger.info(f"Execution ARN: {response.get('executionArn')}")
            logger.info(f"Full response: {json.dumps(response, default=str, indent=2)}")
        except ClientError as sf_err:
            logger.error(f"Step Functions ClientError: {str(sf_err)}")
            logger.error(f"Error code: {sf_err.response.get('Error', {}).get('Code')}")
            logger.error(f"Error message: {sf_err.response.get('Error', {}).get('Message')}")
            raise
        
        success_response = {
            'executionArn': response['executionArn'],
            'startDate': response['startDate'].isoformat()
        }
        logger.info(f"Success response: {json.dumps(success_response, default=str)}")
        logger.info("=== ADMIN RUN MAPPING SUCCESS ===")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(success_response)
        }
    except ClientError as e:
        error_msg = f"AWS ClientError starting Step Functions execution: {str(e)}"
        logger.error("=== ADMIN RUN MAPPING CLIENT ERROR ===")
        logger.error(error_msg)
        logger.error(f"Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
        logger.error(f"Error message: {e.response.get('Error', {}).get('Message', 'Unknown')}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': error_msg})
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error("=== ADMIN RUN MAPPING ERROR ===")
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Log environment info
        logger.error(f"Python version: {sys.version}")
        logger.error(f"Environment vars: {json.dumps(dict(os.environ), indent=2)}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': error_msg})
        }