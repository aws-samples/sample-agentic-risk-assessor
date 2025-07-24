import json
import boto3
import os
import sys
sys.path.append('/opt/python')
sys.path.append('.')

from shared.base_lambda import BaseLambda
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

class AssessmentContent(BaseLambda):
    def __init__(self):
        super().__init__()

    def lambda_handler(self, event, context):
        try:
            print(f"Event received: {json.dumps(event)}")
            
            # Handle OPTIONS request
            if event['requestContext']['http']['method'] == 'OPTIONS':
                return self.handle_options()
            
            # Get assessment type and IDs from path
            path = event.get('rawPath', event.get('path', ''))
            print(f"Path: {path}")
            assessment_type = self._get_assessment_type(path)
            print(f"Assessment type: {assessment_type}")
            
            if not assessment_type:
                return self.handle_error('Invalid assessment type', 400)
            
            project_id = event['pathParameters']['id']
            print(f"Project ID: {project_id}")
            
            # Handle different path parameter names for different assessment types
            if assessment_type == 'architecture':
                assessment_id = event['pathParameters'].get('review_id')
            else:
                assessment_id = event['pathParameters'].get('assessment_id')
            
            print(f"Assessment ID: {assessment_id}")
            print(f"Path parameters: {event['pathParameters']}")
            
            if not project_id:
                return self.handle_error('Missing project_id', 400)
            
            if not assessment_id:
                return self.handle_error('Missing assessment_id', 400)
            
            return self._get_assessment_content(project_id, assessment_id, assessment_type)
            
        except Exception as e:
            print(f"Error in assessment content: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return self.handle_error(f'Failed to get assessment content: {str(e)}')

    def _get_assessment_type(self, path):
        """Determine assessment type from path"""
        if 'risk-assessment' in path or 'risk_assessment' in path:
            return 'risk'
        elif 'security-assessment' in path or 'security_assessment' in path:
            return 'security'
        elif 'architecture-review' in path or 'architecture_review' in path:
            return 'architecture'
        return None

    def _get_assessment_content(self, project_id, assessment_id, assessment_type):
        """Get assessment content from S3 (replaces get_*_content.py functions)"""
        try:
            print(f"Getting project: {project_id}")
            project = self.get_project(project_id)
            
            if not project:
                print(f"Project not found: {project_id}")
                return self.handle_error('Project not found', 404)
            
            print(f"Project found, getting assessments for type: {assessment_type}")
            
            # Get assessments based on type
            if assessment_type == 'risk':
                assessments = project.get('risk_assessments', [])
            elif assessment_type == 'security':
                assessments = project.get('security_assessments', []) or project.get('control_gap_assessments', [])
            elif assessment_type == 'architecture':
                assessments = project.get('architecture_reviews', [])
            else:
                return self.handle_error('Invalid assessment type', 400)
            
            print(f"Found {len(assessments)} assessments of type {assessment_type}")
            print(f"Assessments: {json.dumps(assessments, cls=DecimalEncoder)}")
            
            # Handle 'latest' - return the most recent assessment
            if assessment_id == 'latest' and assessments:
                assessments_sorted = sorted(assessments, key=lambda a: a.get('created_at', ''), reverse=True)
                assessment = assessments_sorted[0]
            # Find the specific assessment
            elif assessment_type == 'architecture':
                assessment = next((a for a in assessments if a.get('review_id') == assessment_id), None)
            else:
                assessment = next((a for a in assessments if a.get('assessment_id') == assessment_id), None)
            
            if not assessment:
                print(f"Assessment not found: {assessment_id}")
                return self.handle_error('Assessment not found', 404)
            
            print(f"Found assessment: {json.dumps(assessment, cls=DecimalEncoder)}")
            
            # Get content from S3
            try:
                s3_key = assessment.get('s3_key')
                if not s3_key:
                    print(f"No s3_key found in assessment")
                    return self.handle_error('No content key found for assessment', 404)
                
                print(f"Getting S3 object: bucket={self.documents_bucket}, key={s3_key}")
                obj = self.s3.get_object(Bucket=self.documents_bucket, Key=s3_key)
                content = obj['Body'].read().decode('utf-8')
                
                print(f"Successfully retrieved content, length: {len(content)}")
                
                return self.success_response({
                    'content': content,
                    'filename': assessment.get('filename', ''),
                    'version': assessment.get('version', 1),
                    'assessment_id': assessment_id,
                    'type': assessment_type,
                    'created_at': assessment.get('created_at', ''),
                    'framework': assessment.get('framework', '')
                })
                
            except Exception as s3_error:
                print(f"S3 error: {str(s3_error)}")
                import traceback
                print(f"S3 traceback: {traceback.format_exc()}")
                return self.handle_error('Failed to get content from S3', 500)
            
        except Exception as e:
            print(f"General error: {str(e)}")
            import traceback
            print(f"General traceback: {traceback.format_exc()}")
            return self.handle_error(f'Failed to get {assessment_type} assessment content: {str(e)}')

# Lambda handler
def lambda_handler(event, context):
    print("LAMBDA HANDLER CALLED")
    content_handler = AssessmentContent()
    return content_handler.lambda_handler(event, context)