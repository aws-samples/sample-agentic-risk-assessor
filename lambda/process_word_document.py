import json
import boto3
import os
import uuid
import base64
from datetime import datetime
import io
import traceback
import pypandoc
import tempfile
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
projects_table = dynamodb.Table(os.environ.get('PROJECTS_TABLE', 'Projects'))
documents_bucket = os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents-development')
diagrams_bucket = os.environ.get('DIAGRAMS_BUCKET')

def lambda_handler(event, context):
    try:
        logger.info(f"Lambda handler started - Request ID: {context.aws_request_id}")
        # Log event without body content for security
        event_summary = {
            'requestContext': event.get('requestContext', {}),
            'headers': event.get('headers', {}),
            'queryStringParameters': event.get('queryStringParameters'),
            'pathParameters': event.get('pathParameters'),
            'body_size': len(event.get('body', '')) if event.get('body') else 0
        }
        logger.info(f"Event received: {json.dumps(event_summary, default=str)}")
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE'
        }
        
        if event['requestContext']['http']['method'] == 'OPTIONS':
            logger.info("Handling OPTIONS request")
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({})}
        
        body = json.loads(event['body'])
        project_id = body.get('project_id')
        file_content_base64 = body.get('file_content')
        file_name = body.get('file_name')
        
        # Validate file type
        file_extension = os.path.splitext(file_name)[1].lower() if file_name else ''
        if file_extension not in ['.docx', '.pdf']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Unsupported file type. Only DOCX and PDF files are supported.'})
            }
        
        logger.info(f"Processing request - Project ID: {project_id}, File: {file_name}, Type: {file_extension}")
        logger.info(f"File content size: {len(file_content_base64) if file_content_base64 else 0} characters")
        
        if not project_id or not file_content_base64 or not file_name:
            logger.error(f"Missing required parameters - project_id: {bool(project_id)}, file_content: {bool(file_content_base64)}, file_name: {bool(file_name)}")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Check if project exists
        logger.info(f"Checking if project exists: {project_id}")
        project = projects_table.get_item(Key={'id': project_id}).get('Item')
        if not project:
            logger.error(f"Project not found: {project_id}")
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Project not found'})
            }
        logger.info(f"Project found: {project.get('name', 'Unknown')}")
        
        # Decode file content
        logger.info("Decoding base64 file content")
        try:
            file_content = base64.b64decode(file_content_base64)
            logger.info(f"File decoded successfully - Size: {len(file_content)} bytes")
        except Exception as decode_error:
            logger.error(f"Failed to decode base64 content: {str(decode_error)}")
            raise decode_error
        
        # Process document (DOCX or PDF)
        logger.info(f"Starting document processing for {file_extension}")
        result = process_word_document(file_content, project_id, file_name, file_extension)
        logger.info("Word document processing completed successfully")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error processing Word document: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to process Word document'})
        }

def process_word_document(file_content, project_id, file_name, file_extension='.docx'):
    """Process document (DOCX or PDF): store original for display, extract text for AI"""
    logger.info(f"Starting document processing for project {project_id}, file: {file_name}, type: {file_extension}")
    
    # Determine content type and file extension
    if file_extension == '.pdf':
        content_type = 'application/pdf'
        file_ext = '.pdf'
    else:
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        file_ext = '.docx'
    
    # Store original document for frontend display
    doc_key = f"projects/{project_id}/documents/{uuid.uuid4()}{file_ext}"
    logger.info(f"Generated S3 key for document: {doc_key}")
    logger.info(f"Uploading document to S3 bucket: {documents_bucket}")
    try:
        s3.put_object(
            Bucket=documents_bucket,
            Key=doc_key,
            Body=file_content,
            ContentType=content_type
        )
        logger.info("Document uploaded to S3 successfully")
    except Exception as s3_error:
        logger.error(f"Failed to upload document to S3: {str(s3_error)}")
        raise s3_error
    
    # Generate presigned URL for frontend access
    logger.info("Generating presigned URL for document access")
    try:
        document_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': documents_bucket, 'Key': doc_key},
            ExpiresIn=3600
        )
        logger.info("Presigned URL generated successfully")
    except Exception as url_error:
        logger.error(f"Failed to generate presigned URL: {str(url_error)}")
        raise url_error
    
    # Convert document to Markdown using pypandoc with layer
    logger.info(f"Starting {file_extension.upper()} to Markdown conversion")
    try:
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_docx:
            logger.info(f"Created temporary file: {temp_docx.name}")
            temp_docx.write(file_content)
            temp_docx.flush()
            logger.info(f"Written {len(file_content)} bytes to temporary file")
            
            # Create secure temp directory for extracted media
            media_dir = tempfile.mkdtemp(prefix='media_', dir='/tmp')
            logger.info(f"Created media directory: {media_dir}")
            
            # Convert using pypandoc
            logger.info(f"Converting {file_extension.upper()} to Markdown using pypandoc")
            if file_extension == '.pdf':
                # PDF - simple text extraction
                markdown_content = pypandoc.convert_file(
                    temp_docx.name, 
                    'md',
                    extra_args=['--wrap=none']
                )
            else:
                # DOCX with media extraction
                markdown_content = pypandoc.convert_file(
                    temp_docx.name, 
                    'md',
                    extra_args=['--wrap=none', f'--extract-media={media_dir}']
                )
            logger.info(f"Conversion successful - Markdown length: {len(markdown_content)} characters")
            
            # Upload extracted images to diagrams bucket (DOCX only)
            if file_extension == '.docx':
                markdown_content = upload_extracted_images(markdown_content, media_dir, project_id)
            
            # Clean up temp files
            os.unlink(temp_docx.name)
            import shutil
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)
            logger.info("Temporary files cleaned up")
            
    except Exception as e:
        logger.error(f"Pandoc conversion failed: {str(e)}")
        logger.error(f"Conversion error traceback: {traceback.format_exc()}")
        raise e
    
    # Store converted markdown for AI agents
    md_key = f"projects/{project_id}/documents/{uuid.uuid4()}.md"
    logger.info(f"Generated S3 key for Markdown document: {md_key}")
    
    try:
        s3.put_object(
            Bucket=documents_bucket,
            Key=md_key,
            Body=markdown_content.encode('utf-8'),
            ContentType='text/markdown'
        )
        logger.info("Markdown document uploaded to S3 successfully")
    except Exception as md_s3_error:
        logger.error(f"Failed to upload Markdown document to S3: {str(md_s3_error)}")
        raise md_s3_error
    
    # Update project with document metadata
    timestamp = datetime.now().isoformat()
    logger.info(f"Updating project {project_id} with document metadata")
    
    try:
        projects_table.update_item(
            Key={'id': project_id},
            UpdateExpression="set document_key = :dk, document_name = :dn, document_type = :dt, document_uploaded_at = :du, document_text_key = :dtk, document_url = :durl",
            ExpressionAttributeValues={
                ':dk': doc_key,  # Frontend uses original document
                ':dn': file_name,
                ':dt': content_type,
                ':du': timestamp,
                ':dtk': md_key,  # AI uses simple text
                ':durl': document_url
            }
        )
        logger.info("Project updated with document metadata successfully")
    except Exception as db_error:
        logger.error(f"Failed to update project in DynamoDB: {str(db_error)}")
        raise db_error
    
    result = {
        'message': f'{file_extension.upper()} document processed successfully',
        'document_key': doc_key,
        'document_name': file_name,
        'document_url': document_url,
        'text_key': md_key
    }
    
    # Add image URL if diagram was extracted
    if hasattr(upload_extracted_images, 'first_image_filename') and upload_extracted_images.first_image_filename:
        api_gateway_url = os.environ.get('API_GATEWAY_URL', '')
        result['diagram_url'] = f"{api_gateway_url}/api/images/{upload_extracted_images.first_image_filename}"
    
    # Log result without sensitive URLs
    result_summary = {
        'message': result['message'],
        'document_name': result['document_name'],
        'keys_generated': bool(result['document_key'] and result['text_key'])
    }
    logger.info(f"Document processing completed successfully: {json.dumps(result_summary)}")
    return result

def upload_extracted_images(markdown_content, media_dir, project_id):
    """Upload extracted images to S3 and update markdown references"""
    import re
    import glob
    
    logger.info(f"Processing extracted images from {media_dir}")
    
    # Find all image files in media directory
    image_files = glob.glob(f"{media_dir}/**/*", recursive=True)
    image_files = [f for f in image_files if os.path.isfile(f) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    
    logger.info(f"Found {len(image_files)} image files")
    
    first_image_filename = None
    
    for idx, image_path in enumerate(image_files):
        try:
            # Generate unique filename
            original_name = os.path.basename(image_path)
            file_ext = os.path.splitext(original_name)[1]
            new_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Store first image filename for diagram functionality
            if idx == 0:
                first_image_filename = new_filename
            
            # Upload to diagrams bucket at root level
            with open(image_path, 'rb') as img_file:
                s3.put_object(
                    Bucket=diagrams_bucket,
                    Key=new_filename,  # Store at root level for images API
                    Body=img_file.read(),
                    ContentType=f'image/{file_ext[1:]}'
                )
            
            logger.info(f"Uploaded image: {new_filename}")
            
            # Update markdown references - replace with just filename
            old_path = image_path.replace(media_dir, '').lstrip('/')
            full_temp_path = f"{media_dir}/{old_path}"
            markdown_content = markdown_content.replace(full_temp_path, new_filename)
            
            logger.info(f"Replaced {full_temp_path} with {new_filename}")
            
        except Exception as e:
            logger.error(f"Failed to upload image {image_path}: {str(e)}")
    
    # Set first image as diagram if any images were found
    if first_image_filename:
        try:
            projects_table.update_item(
                Key={'id': project_id},
                UpdateExpression="set diagram_filename = :df",
                ExpressionAttributeValues={':df': first_image_filename}
            )
            logger.info(f"Set diagram_filename to: {first_image_filename}")
        except Exception as e:
            logger.error(f"Failed to set diagram_filename: {str(e)}")
    
    # Store first image filename for return value
    upload_extracted_images.first_image_filename = first_image_filename
    
    logger.info(f"Final markdown content preview: {markdown_content[:500]}...")
    return markdown_content

