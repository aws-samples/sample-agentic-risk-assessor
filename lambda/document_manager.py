import json
import boto3
import os
import uuid
import base64
import mimetypes
from datetime import datetime
import traceback
import sys
sys.path.append('/opt/python')
sys.path.append('.')

from shared.base_lambda import BaseLambda

class DocumentManager(BaseLambda):
    def __init__(self):
        super().__init__()
        self.diagrams_bucket = os.environ.get('DIAGRAMS_BUCKET')

    def lambda_handler(self, event, context):
        try:
            # Handle OPTIONS request
            if event['requestContext']['http']['method'] == 'OPTIONS':
                return self.handle_options()
            
            # Route based on path and method
            path = event.get('rawPath', event.get('path', ''))
            method = event['requestContext']['http']['method']
            
            if '/upload' in path and method == 'POST':
                return self._handle_upload(event)
            elif '/content' in path and method == 'GET':
                return self._handle_get_content(event)
            elif method == 'GET':
                return self._handle_get_document(event)
            else:
                return self.handle_error('Invalid operation', 400)
                
        except Exception as e:
            print(f"Error in document manager: {str(e)}")
            print(traceback.format_exc())
            return self.handle_error(f'Document operation failed: {str(e)}')

    def _handle_upload(self, event):
        """Handle document upload (replaces process_document.py)"""
        try:
            body = json.loads(event['body'])
            project_id = body.get('project_id')
            file_content_base64 = body.get('file_content')
            file_name = body.get('file_name')
            file_type = body.get('file_type')
            
            if not all([project_id, file_content_base64, file_name]):
                return self.handle_error('Missing required parameters', 400)
            
            # Check if project exists
            project = self.get_project(project_id)
            if not project:
                return self.handle_error('Project not found', 404)
            
            # Decode and upload file
            file_content = base64.b64decode(file_content_base64)
            file_size = len(file_content)
            file_extension = os.path.splitext(file_name)[1].lower()
            s3_key = f"projects/{project_id}/documents/{uuid.uuid4()}{file_extension}"
            
            content_type = file_type or mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
            self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Handle image files for diagram functionality
            diagram_filename = None
            if file_extension.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']:
                diagram_filename = f"{uuid.uuid4().hex}{file_extension}"
                try:
                    self.s3.put_object(
                        Bucket=self.diagrams_bucket,
                        Key=diagram_filename,
                        Body=file_content,
                        ContentType=content_type
                    )
                except Exception as s3_error:
                    print(f"Failed to upload image to diagrams bucket: {str(s3_error)}")
                    diagram_filename = None
            
            # Extract and store text
            extracted_text = self._extract_text(file_content, file_extension)
            text_key = f"{s3_key}.txt"
            self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=text_key,
                Body=extracted_text,
                ContentType='text/plain'
            )
            
            # Update project
            timestamp = datetime.now().isoformat()
            update_expression = "set document_key = :dk, document_name = :dn, document_type = :dt, document_size = :ds, document_uploaded_at = :du, document_text_key = :dtk"
            expression_values = {
                ':dk': s3_key,
                ':dn': file_name,
                ':dt': content_type,
                ':ds': file_size,
                ':du': timestamp,
                ':dtk': text_key
            }
            
            if diagram_filename:
                update_expression += ", diagram_filename = :df"
                expression_values[':df'] = diagram_filename
            
            self.update_project(project_id, update_expression, expression_values)
            
            result = {
                'message': 'Document uploaded successfully',
                'document_key': s3_key,
                'document_name': file_name
            }
            
            if diagram_filename:
                result['diagram_url'] = f"{os.environ.get('API_GATEWAY_URL', '')}/api/images/{diagram_filename}"
            
            return self.success_response(result)
            
        except Exception as e:
            return self.handle_error(f'Upload failed: {str(e)}')

    def _handle_get_document(self, event):
        """Handle get document metadata (replaces get_document.py)"""
        try:
            project_id = event['pathParameters']['id']
            project = self.get_project(project_id)
            
            if not project:
                return self.handle_error('Project not found', 404)
            
            if 'document_key' not in project:
                return self.handle_error('No document found for this project', 404)
            
            # Generate pre-signed URL
            document_url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.documents_bucket,
                    'Key': project['document_key']
                },
                ExpiresIn=3600
            )
            
            return self.success_response({
                'document_name': project.get('document_name', ''),
                'document_type': project.get('document_type', ''),
                'document_size': project.get('document_size', 0),
                'document_uploaded_at': project.get('document_uploaded_at', ''),
                'download_url': document_url
            })
            
        except Exception as e:
            return self.handle_error(f'Failed to get document: {str(e)}')

    def _handle_get_content(self, event):
        """Handle get document content (replaces get_document_content.py)"""
        try:
            project_id = event['pathParameters']['id']
            project = self.get_project(project_id)
            
            if not project:
                return self.handle_error('Project not found', 404)
            
            if 'document_text_key' not in project:
                return self.handle_error('No document content found for this project', 404)
            
            try:
                response = self.s3.get_object(Bucket=self.documents_bucket, Key=project['document_text_key'])
                content = response['Body'].read().decode('utf-8')
                
                return self.success_response({
                    'content': content,
                    'document_name': project.get('document_name', ''),
                    'document_type': project.get('document_type', '')
                })
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    return self.handle_error('Document file not found in storage', 404)
                raise e
                
        except Exception as e:
            return self.handle_error(f'Failed to get document content: {str(e)}')

    def _extract_text(self, file_content, file_extension):
        """Extract text from various document formats"""
        try:
            if file_extension.lower() in ['.txt', '.md', '.rtf']:
                return file_content.decode('utf-8', errors='ignore')
            elif file_extension.lower() in ['.pdf']:
                return "PDF file uploaded - text extraction not available"
            elif file_extension.lower() in ['.docx']:
                return "DOCX file uploaded - text extraction not available"
            else:
                return f"Unsupported file format: {file_extension}"
        except Exception as e:
            return f"Error extracting text: {str(e)}"

# Lambda handler
def lambda_handler(event, context):
    manager = DocumentManager()
    return manager.lambda_handler(event, context)