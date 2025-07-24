import json
import boto3
import os
import sys
from decimal import Decimal
sys.path.append('/opt/python')
sys.path.append('.')

from shared.base_lambda import BaseLambda

class AssessmentRetriever(BaseLambda):
    def __init__(self):
        super().__init__()

    def lambda_handler(self, event, context):
        try:
            # Handle OPTIONS request
            if event['requestContext']['http']['method'] == 'OPTIONS':
                return self.handle_options()
            
            # Get assessment type from path
            path = event.get('rawPath', event.get('path', ''))
            assessment_type = self._get_assessment_type(path)
            
            if not assessment_type:
                return self.handle_error('Invalid assessment type', 400)
            
            project_id = event['pathParameters']['id']
            
            if not project_id:
                return self.handle_error('Missing project_id', 400)
            
            return self._get_assessments(project_id, assessment_type)
            
        except Exception as e:
            print(f"Error in assessment retriever: {str(e)}")
            return self.handle_error(f'Failed to get assessments: {str(e)}')

    def _get_assessment_type(self, path):
        """Determine assessment type from path"""
        if 'risk-assessment' in path or 'risk_assessment' in path:
            return 'risk'
        elif 'security-assessment' in path or 'security_assessment' in path:
            return 'security'
        elif 'architecture-review' in path or 'architecture_review' in path:
            return 'architecture'
        return None

    def _get_assessments(self, project_id, assessment_type):
        """Get assessments by type (replaces get_risk_assessments.py, get_security_assessments.py, get_architecture_reviews.py)"""
        try:
            project = self.get_project(project_id)
            
            if not project:
                return self.handle_error('Project not found', 404)
            
            # Get assessments based on type
            if assessment_type == 'risk':
                assessments = project.get('risk_assessments', [])
            elif assessment_type == 'security':
                # Check both new and legacy fields
                assessments = project.get('security_assessments', []) or project.get('control_gap_assessments', [])
            elif assessment_type == 'architecture':
                assessments = project.get('architecture_reviews', [])
            else:
                return self.handle_error('Invalid assessment type', 400)
            
            # Convert Decimal objects and sort by creation date (newest first)
            assessments = self._convert_decimals(assessments)
            assessments.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return self.success_response({
                'project_id': project_id,
                'assessments': assessments,
                'count': len(assessments),
                'type': assessment_type
            })
            
        except Exception as e:
            return self.handle_error(f'Failed to get {assessment_type} assessments: {str(e)}')

    def _convert_decimals(self, obj):
        """Convert Decimal objects to regular types"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return obj

# Lambda handler
def lambda_handler(event, context):
    retriever = AssessmentRetriever()
    return retriever.lambda_handler(event, context)