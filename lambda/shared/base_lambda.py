import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import ClientError

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

class BaseLambda:
    def __init__(self):
        self.headers = self._get_cors_headers()
        self.dynamodb = boto3.resource('dynamodb')
        self.dynamodb_client = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        self.projects_table_name = os.environ.get('PROJECTS_TABLE', 'Projects')
        self.projects_table = self.dynamodb.Table(self.projects_table_name)
        self.documents_bucket = os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents-development')
    
    def _get_cors_headers(self):
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
        }
    
    def handle_options(self):
        return {
            'statusCode': 200,
            'headers': self.headers,
            'body': json.dumps({})
        }
    
    def handle_error(self, error, status_code=500):
        return {
            'statusCode': status_code,
            'headers': self.headers,
            'body': json.dumps({'error': str(error)}, cls=DecimalEncoder)
        }
    
    def success_response(self, data, status_code=200):
        return {
            'statusCode': status_code,
            'headers': self.headers,
            'body': json.dumps(data, cls=DecimalEncoder)
        }
    
    def get_project(self, project_id):
        """Get project from DynamoDB"""
        try:
            response = self.projects_table.get_item(Key={'id': project_id})
            return response.get('Item')
        except Exception as e:
            raise Exception(f"Failed to get project {project_id}: {str(e)}")
    
    def update_project(self, project_id, update_expression, expression_values):
        """Update project in DynamoDB"""
        try:
            self.projects_table.update_item(
                Key={'id': project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
        except Exception as e:
            raise Exception(f"Failed to update project {project_id}: {str(e)}")