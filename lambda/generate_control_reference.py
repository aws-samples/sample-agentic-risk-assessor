import json
import boto3
import logging
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

APP_BUCKET = os.environ.get('APP_DATA_BUCKET', 'risk-agent-app-data-a57fe9d3')
TEMPLATE_KEY = 'templates/control_reference_template.html'
OUTPUT_PREFIX = 'control-references'


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)


def lambda_handler(event, context):
    """Generate a static HTML control reference page for a service/framework."""
    service = event.get('service')
    framework = event.get('framework')

    logger.info(f"Generating control reference for {service}/{framework}")

    if not service or not framework:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing service or framework'})}

    try:
        # 1. Get template from S3
        template_resp = s3.get_object(Bucket=APP_BUCKET, Key=TEMPLATE_KEY)
        template = template_resp['Body'].read().decode('utf-8')

        # 2. Query all controls for this service/framework
        table = dynamodb.Table(os.environ.get('SERVICE_CONTROLS_TABLE', 'risk-agent-service_controls'))
        controls = []

        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ServiceName').eq(service) &
            boto3.dynamodb.conditions.Key('Framework').begins_with(framework)
        )
        for item in resp['Items']:
            if item.get('ItemType') == 'CONTROL' and 'ControlData' in item:
                controls.append(item['ControlData'])
            elif 'ApplicableControls' in item:
                controls.extend(item['ApplicableControls'])

        while 'LastEvaluatedKey' in resp:
            resp = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('ServiceName').eq(service) &
                boto3.dynamodb.conditions.Key('Framework').begins_with(framework),
                ExclusiveStartKey=resp['LastEvaluatedKey']
            )
            for item in resp['Items']:
                if item.get('ItemType') == 'CONTROL' and 'ControlData' in item:
                    controls.append(item['ControlData'])
                elif 'ApplicableControls' in item:
                    controls.extend(item['ApplicableControls'])

        controls.sort(key=lambda c: c.get('id', ''))
        logger.info(f"Found {len(controls)} controls")

        if not controls:
            return {'statusCode': 200, 'body': json.dumps({'message': 'No controls found', 'service': service, 'framework': framework})}

        # 3. Build framework display name
        framework_names = {
            'nist': 'NIST 800-53 Rev 5',
            'cri': 'CRI Profile 2.0',
            'pci_dss': 'PCI DSS 4.0',
            'iso27001': 'ISO 27001:2022',
            'cis': 'CIS Controls v8',
            'hipaa': 'HIPAA Security Rule',
            'apra_cps234': 'APRA CPS 234',
        }
        framework_display = framework_names.get(framework, framework.upper())

        # 4. Inject data into template
        control_data = json.dumps({'service': service, 'framework': framework_display, 'controls': controls}, cls=DecimalEncoder)
        html = template.replace('{{CONTROL_DATA}}', control_data)
        html = html.replace('{{SERVICE}}', service)
        html = html.replace('{{FRAMEWORK}}', framework_display)

        # 5. Upload to S3
        safe_service = service.replace(' ', '_').replace('/', '_')
        output_key = f"{OUTPUT_PREFIX}/{framework}/{safe_service}.html"

        s3.put_object(
            Bucket=APP_BUCKET,
            Key=output_key,
            Body=html.encode('utf-8'),
            ContentType='text/html'
        )

        logger.info(f"Generated reference: s3://{APP_BUCKET}/{output_key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'service': service,
                'framework': framework,
                'controls_count': len(controls),
                's3_key': output_key,
                'bucket': APP_BUCKET
            })
        }

    except Exception as e:
        logger.error(f"Error generating control reference: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
