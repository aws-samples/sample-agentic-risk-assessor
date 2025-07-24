"""
Lambda function to get organization profile content
"""
import json
import re
from shared.base_lambda import BaseLambda
from shared.profile_s3_operations import ProfileS3Operations

class GetProfileLambda(BaseLambda):
    def __init__(self):
        super().__init__()
        # Use centralized S3 operations for organization profiles
        self.profile_ops = ProfileS3Operations(s3_client=self.s3, documents_bucket=self.documents_bucket)
    
    def extract_metadata_from_content(self, content):
        """Extract metadata fields from profile content"""
        metadata = {
            'industry': 'Unknown',
            'size': 'Unknown', 
            'regions': [],
            'completeness': 0
        }
        
        if not content:
            return metadata
            
        # Extract industry - match the actual format in the content
        industry_match = re.search(r'\*\*Industry:\*\*\s*([^\n]+)', content, re.IGNORECASE)
        if industry_match:
            metadata['industry'] = industry_match.group(1).strip()
            
        # Extract size - match the actual format in the content  
        size_match = re.search(r'\*\*Size:\*\*\s*([^\n]+)', content, re.IGNORECASE)
        if size_match:
            metadata['size'] = size_match.group(1).strip()
            
        # Extract regions - match "Primary Region" (singular)
        regions_match = re.search(r'\*\*Primary Region:\*\*\s*([^\n]+)', content, re.IGNORECASE)
        if regions_match:
            regions_text = regions_match.group(1).strip()
            metadata['regions'] = [r.strip() for r in regions_text.split(',')]
            
        # Calculate completeness based on filled fields
        required_fields = [
            r'\*\*Organization Name:\*\*\s*[^\s\n]',
            r'\*\*Industry:\*\*\s*[^\s\n]',
            r'\*\*Size:\*\*\s*[^\s\n]',
            r'\*\*Primary Region:\*\*\s*[^\s\n]'
        ]
        
        filled_fields = sum(1 for pattern in required_fields if re.search(pattern, content, re.IGNORECASE))
        metadata['completeness'] = int((filled_fields / len(required_fields)) * 100)
        
        return metadata

def lambda_handler(event, context):
    """Get organization profile content by ID"""
    handler = GetProfileLambda()
    
    try:
        # Handle CORS preflight
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return handler.handle_options()
        
        # Get profile ID from path parameters
        profile_id = event.get('pathParameters', {}).get('id')
        if not profile_id:
            return handler.handle_error('Profile ID is required', 400)
        
        # Get profile using centralized operations
        try:
            profile_data = handler.profile_ops.get_profile(profile_id)
            
            # Extract metadata from content
            extracted_metadata = handler.extract_metadata_from_content(profile_data.get('content', ''))
            print(f"Extracted metadata: {extracted_metadata}")
            
            # Merge extracted metadata with existing metadata
            if 'metadata' not in profile_data:
                profile_data['metadata'] = {}
            profile_data['metadata'].update(extracted_metadata)
            
            print(f"Final metadata: {profile_data['metadata']}")
            
            return handler.success_response(profile_data)
            
        except Exception as e:
            if "not found" in str(e).lower():
                return handler.handle_error('Profile not found', 404)
            raise e
        
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        return handler.handle_error(f'Failed to get profile: {str(e)}')