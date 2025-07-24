import json
import os
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

def decimal_default(obj):
    """Convert Decimal to int or float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def normalize_control(control):
    """
    Return ALL fields from control object, converting Decimals to numbers
    """
    # Convert any Decimal values to int/float for JSON serialization
    normalized = {}
    for key, value in control.items():
        if isinstance(value, Decimal):
            normalized[key] = int(value) if value % 1 == 0 else float(value)
        else:
            normalized[key] = value
    return normalized

def lambda_handler(event, context):
    """
    Handler for admin/services endpoint
    GET: Returns list of AWS services with their controls from DynamoDB filtered by framework
    POST: Adds a new service to DynamoDB
    """
    print(f"Event received: {json.dumps(event)}")
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': ''
            }
        
        # This function only handles GET requests
        # POST requests should go to admin_add_service Lambda function
        
        # Handle GET request for listing services
        # Get framework from query parameters
        framework = event.get('queryStringParameters', {}).get('framework', 'all') if event.get('queryStringParameters') else 'all'
        print(f"Framework filter: {framework}")
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        services_table_name = os.environ.get('DYNAMODB_SERVICES_TABLE', 'risk-agent-services')
        controls_table_name = os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls')
        print(f"Using tables: services={services_table_name}, controls={controls_table_name}")
        
        services_table = dynamodb.Table(services_table_name)
        controls_table = dynamodb.Table(controls_table_name)
        
        # First, get all active services from services table
        print("Scanning services table for active services...")
        services_response = services_table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={':status': 'ACTIVE'}
        )
        active_services = services_response.get('Items', [])
        print(f"Found {len(active_services)} active services: {[s.get('ServiceName') for s in active_services]}")
        
        if not active_services:
            print("No active services found, returning empty list")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({'services': []})
            }
        
        # Then get controls for each service based on framework filter
        services = []
        print(f"Processing controls for {len(active_services)} services...")
        
        for i, service in enumerate(active_services):
            service_name = service['ServiceName']
            print(f"Processing service {i+1}/{len(active_services)}: {service_name}")
            
            try:
                # Get controls for this service
                if framework == 'all':
                    controls_response = controls_table.query(
                        KeyConditionExpression='ServiceName = :service_name',
                        ExpressionAttributeValues={':service_name': service_name}
                    )
                else:
                    # Query both old format (Framework=nist) and new format (Framework begins_with nist#CTRL#)
                    controls_response = controls_table.query(
                        KeyConditionExpression='ServiceName = :service_name AND begins_with(Framework, :framework)',
                        ExpressionAttributeValues={
                            ':service_name': service_name,
                            ':framework': framework
                        }
                    )
                
                print(f"Found {len(controls_response.get('Items', []))} control records for {service_name}")
            except Exception as e:
                print(f"Error querying controls for {service_name}: {str(e)}")
                controls_response = {'Items': []}
            
            # Combine service info with controls — support both old and new storage formats
            service_controls = controls_response.get('Items', [])
            
            # Separate old-format items (have ApplicableControls list) from new-format items (have ControlData)
            old_format_items = [item for item in service_controls if 'ApplicableControls' in item]
            new_format_items = [item for item in service_controls if item.get('ItemType') == 'CONTROL' and 'ControlData' in item]
            
            # Build the aggregated service data
            applicable_controls = []
            status = 'PENDING'
            processed_at = service.get('CreatedAt', '')
            
            # Collect from old format
            for item in old_format_items:
                applicable_controls.extend(item.get('ApplicableControls', []))
                if item.get('Status') in ('COMPLETE', 'PROCESSING'):
                    status = item.get('Status', status)
                if item.get('ProcessedAt'):
                    processed_at = item['ProcessedAt']
            
            # Collect from new format
            for item in new_format_items:
                ctrl = item['ControlData']
                applicable_controls.append(ctrl)
                if item.get('ProcessedAt'):
                    processed_at = item['ProcessedAt']
            
            if new_format_items:
                status = 'COMPLETE' if not old_format_items else status
            
            # Trim controls to reduce response size — keep summary + key fields
            summary_fields = ['id', 'name', 'category', 'priority', 'description', 'criticality_score', 
                            'complexity', 'cost_category', 'requirement', 'framework', 'service',
                            'basic_level', 'managed_level', 'optimized_level', 'predictive_level',
                            'implementation_approach', 'capabilities', 'cli_commands', 'prerequisites',
                            'conflicts', 'audit_evidence', 'validation_procedures', 'automated_checks',
                            'monitoring_setup']
            trimmed_controls = []
            for ctrl in applicable_controls:
                trimmed = {}
                for field in summary_fields:
                    if field in ctrl and ctrl[field]:
                        val = str(ctrl[field])
                        # Truncate very long fields to keep response manageable
                        if len(val) > 2000:
                            val = val[:2000] + '...'
                        trimmed[field] = val
                trimmed_controls.append(trimmed)
            applicable_controls = trimmed_controls
            
            if applicable_controls:
                service_data = {
                    'ServiceName': service_name,
                    'ApplicableControls': applicable_controls,
                    'NonApplicableControls': [],
                    'ProcessedAt': processed_at,
                    'Status': status
                }
                print(f"Aggregated {len(applicable_controls)} controls for {service_name} (old={len(old_format_items)}, new={len(new_format_items)})")
            else:
                # Create empty service data if no controls exist yet
                service_data = {
                    'ServiceName': service_name,
                    'ApplicableControls': [],
                    'NonApplicableControls': [],
                    'ProcessedAt': service.get('CreatedAt', ''),
                    'Status': 'PENDING'
                }
                print(f"No controls found for {service_name}, using empty data")
            
            services.append(service_data)
        
        # Normalize all control objects
        print(f"Normalizing controls for {len(services)} services...")
        for service in services:
            if 'ApplicableControls' in service and service['ApplicableControls']:
                service['ApplicableControls'] = [normalize_control(control) for control in service['ApplicableControls']]
            if 'NonApplicableControls' in service and service['NonApplicableControls']:
                service['NonApplicableControls'] = [normalize_control(control) for control in service['NonApplicableControls']]
        
        response_body = json.dumps({'services': services})
        print(f"Generated response with {len(response_body)} characters for {len(services)} services")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': response_body
        }
    except ClientError as e:
        print(f"Error retrieving services: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': f"Error retrieving services: {str(e)}"})
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