import json
import boto3
import os
import sys
sys.path.append('/opt/python')
sys.path.append('.')

from shared.base_lambda import BaseLambda

class AssessmentDownloader(BaseLambda):
    def __init__(self):
        super().__init__()

    def lambda_handler(self, event, context):
        try:
            # Handle OPTIONS request
            if event['requestContext']['http']['method'] == 'OPTIONS':
                return self.handle_options()
            
            # Get assessment type and IDs from path
            path = event.get('rawPath', event.get('path', ''))
            assessment_type = self._get_assessment_type(path)
            
            if not assessment_type:
                return self.handle_error('Invalid assessment type', 400)
            
            path_params = event.get('pathParameters') or {}
            project_id = path_params.get('id')
            assessment_id = path_params.get('assessment_id') or path_params.get('review_id')
            
            if not project_id or not assessment_id:
                return self.handle_error('Missing project_id or assessment_id', 400)
            
            return self._generate_download_url(project_id, assessment_id, assessment_type)
            
        except Exception as e:
            print(f"Error in assessment downloader: {str(e)}")
            return self.handle_error(f'Failed to generate download URL: {str(e)}')

    def _get_assessment_type(self, path):
        """Determine assessment type from path"""
        if 'risk-assessment' in path or 'risk_assessment' in path:
            return 'risk'
        elif 'security-assessment' in path or 'security_assessment' in path:
            return 'security'
        elif 'architecture-review' in path or 'architecture_review' in path:
            return 'architecture'
        return None

    def _generate_download_url(self, project_id, assessment_id, assessment_type):
        """Generate presigned download URL (replaces download_*_assessment.py functions)"""
        try:
            project = self.get_project(project_id)
            
            if not project:
                return self.handle_error('Project not found', 404)
            
            # Get assessments based on type
            if assessment_type == 'risk':
                assessments = project.get('risk_assessments', [])
                id_field = 'assessment_id'
            elif assessment_type == 'security':
                assessments = project.get('security_assessments', []) or project.get('control_gap_assessments', [])
                id_field = 'assessment_id'
            elif assessment_type == 'architecture':
                assessments = project.get('architecture_reviews', [])
                id_field = 'review_id'
            else:
                return self.handle_error('Invalid assessment type', 400)
            
            # Find the specific assessment
            assessment = next((a for a in assessments if a.get(id_field) == assessment_id), None)
            if not assessment:
                return self.handle_error(f'{assessment_type.title()} assessment not found', 404)
            
            # Check if S3 key exists
            s3_key = assessment.get('s3_key')
            if not s3_key:
                return self.handle_error('No file key found for assessment', 404)
            
            # Generate presigned URL for download
            try:
                download_params = {
                    'Bucket': self.documents_bucket,
                    'Key': s3_key
                }
                
                # Add content disposition for proper filename
                filename = assessment.get('filename', f'{assessment_type}_assessment_{assessment_id}.md')
                download_params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
                download_params['ResponseContentType'] = 'text/markdown'
                
                download_url = self.s3.generate_presigned_url(
                    'get_object',
                    Params=download_params,
                    ExpiresIn=3600  # 1 hour
                )
                
                return self.success_response({
                    'download_url': download_url,
                    'filename': filename,
                    'version': assessment.get('version', 1),
                    'created_at': assessment.get('created_at', ''),
                    'assessment_id': assessment_id,
                    'type': assessment_type
                })
                
            except Exception as s3_error:
                print(f"S3 error: {str(s3_error)}")
                return self.handle_error('Failed to generate download URL', 500)
            
        except Exception as e:
            return self.handle_error(f'Failed to generate {assessment_type} assessment download URL: {str(e)}')

# Lambda handler
def lambda_handler(event, context):
    downloader = AssessmentDownloader()
    return downloader.lambda_handler(event, context)