import json
import boto3
import uuid
import os
import sys
from datetime import datetime
sys.path.append('/opt/python')
sys.path.append('.')

from shared.base_lambda import BaseLambda

class AssessmentSaver(BaseLambda):
    def __init__(self):
        super().__init__()

    def lambda_handler(self, event, context):
        try:
            # Handle OPTIONS request
            if event['requestContext']['http']['method'] == 'OPTIONS':
                return self.handle_options()
            
            # Parse request body first to get assessment type
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            assessment_type = body.get('assessment_type')
            
            if not assessment_type:
                # Fallback to path-based detection for backward compatibility
                path = event.get('rawPath', event.get('path', ''))
                assessment_type = self._get_assessment_type(path)
            else:
                # Normalize the assessment type from request body
                assessment_type = self._get_assessment_type(assessment_type)
            
            if not assessment_type:
                return self.handle_error('Invalid assessment type', 400)
            
            # Get project ID from path parameters
            project_id = event['pathParameters']['id']
            
            if not project_id:
                return self.handle_error('Missing project_id', 400)
            
            # Parse request body
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            assessment_content = body.get('assessment_content') or body
            
            if not assessment_content:
                return self.handle_error('Missing assessment_content', 400)
            
            return self._save_assessment(project_id, assessment_content, assessment_type)
            
        except Exception as e:
            print(f"Error in assessment saver: {str(e)}")
            return self.handle_error(f'Failed to save assessment: {str(e)}')

    def _get_assessment_type(self, path_or_type):
        """Determine assessment type from path or direct type string"""
        # Handle direct type strings from request body
        if path_or_type in ['architecture-reviews', 'architecture_reviews', 'architecture-review', 'architecture_review', 'architecture']:
            return 'architecture'
        elif path_or_type in ['risk-assessments', 'risk_assessments', 'risk-assessment', 'risk_assessment', 'risk']:
            return 'risk'
        elif path_or_type in ['security-assessments', 'security_assessments', 'security-assessment', 'security_assessment', 'security']:
            return 'security'
        elif path_or_type in ['control-gap-assessments', 'control_gap_assessments', 'control-gap-assessment', 'control_gap_assessment', 'control_gap']:
            return 'control_gap'
        
        # Handle path-based detection for backward compatibility
        if 'risk-assessment' in path_or_type or 'risk_assessment' in path_or_type:
            return 'risk'
        elif 'security-assessment' in path_or_type or 'security_assessment' in path_or_type:
            return 'security'
        elif 'architecture-review' in path_or_type or 'architecture_review' in path_or_type:
            return 'architecture'
        elif 'control-gap-assessment' in path_or_type or 'control_gap_assessment' in path_or_type:
            return 'control_gap'
        return None

    def _save_assessment(self, project_id, assessment_content, assessment_type):
        """Save assessment to S3 and update DynamoDB (replaces save_*_assessment.py functions)"""
        try:
            # Check if project exists
            project = self.get_project(project_id)
            if not project:
                return self.handle_error('Project not found', 404)
            
            # Generate assessment metadata
            assessment_id = str(uuid.uuid4())
            timestamp = datetime.now()
            version = timestamp.strftime("%Y%m%d_%H%M%S")
            
            # Determine filename and S3 path based on type
            if assessment_type == 'risk':
                filename = f"risk_assessment_v{version}.md"
                s3_key = f"projects/{project_id}/risk_assessments/{filename}"
                db_field = 'risk_assessments'
                id_field = 'assessment_id'
            elif assessment_type == 'security':
                filename = f"security_assessment_v{version}.md"
                s3_key = f"projects/{project_id}/security_assessments/{filename}"
                db_field = 'security_assessments'
                id_field = 'assessment_id'
            elif assessment_type == 'architecture':
                filename = f"architecture_review_v{version}.md"
                s3_key = f"projects/{project_id}/architecture_reviews/{filename}"
                db_field = 'architecture_reviews'
                id_field = 'review_id'
            elif assessment_type == 'control_gap':
                filename = f"control_gap_assessment_v{version}.md"
                s3_key = f"projects/{project_id}/control_gap_assessments/{filename}"
                db_field = 'control_gap_assessments'
                id_field = 'assessment_id'
            else:
                return self.handle_error('Invalid assessment type', 400)
            
            # Convert content to string if needed
            if isinstance(assessment_content, dict):
                assessment_content = json.dumps(assessment_content, indent=2)
            elif not isinstance(assessment_content, str):
                assessment_content = str(assessment_content)
            
            # Save assessment to S3
            try:
                self.s3.put_object(
                    Bucket=self.documents_bucket,
                    Key=s3_key,
                    Body=assessment_content.encode('utf-8'),
                    ContentType='text/markdown',
                    Metadata={
                        'project_id': project_id,
                        'assessment_id': assessment_id,
                        'version': version,
                        'created_at': timestamp.isoformat(),
                        'type': assessment_type
                    }
                )
            except Exception as s3_error:
                print(f"S3 error: {str(s3_error)}")
                return self.handle_error('Failed to save assessment to S3', 500)
            
            # Prepare assessment record
            assessment_record = {
                id_field: assessment_id,
                'filename': filename,
                's3_key': s3_key,
                'version': version,
                'created_at': timestamp.isoformat(),
                'file_size': len(assessment_content.encode('utf-8')),
                'type': assessment_type
            }
            
            # Update project with new assessment
            try:
                current_assessments = project.get(db_field, [])
                current_assessments.append(assessment_record)
                
                self.update_project(
                    project_id,
                    f'SET {db_field} = :assessments',
                    {':assessments': current_assessments}
                )
            except Exception as db_error:
                print(f"DynamoDB error: {str(db_error)}")
                return self.handle_error('Failed to update project record', 500)
            
            return self.success_response({
                'message': f'{assessment_type.title()} assessment saved successfully',
                'assessment_id': assessment_id,
                'filename': filename,
                'version': version,
                's3_key': s3_key,
                'type': assessment_type,
                'created_at': timestamp.isoformat()
            })
            
        except Exception as e:
            return self.handle_error(f'Failed to save {assessment_type} assessment: {str(e)}')

# Lambda handler
def lambda_handler(event, context):
    saver = AssessmentSaver()
    return saver.lambda_handler(event, context)