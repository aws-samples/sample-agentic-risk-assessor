"""
Lambda function to list organization profiles
"""
import json
import re
from shared.base_lambda import BaseLambda
from shared.profile_s3_operations import ProfileS3Operations

class ListProfilesLambda(BaseLambda):
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
    """List all available organization profiles with metadata"""
    handler = ListProfilesLambda()
    
    try:
        # Handle CORS preflight
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return handler.handle_options()
        
        # List profiles using centralized operations
        profiles = handler.profile_ops.list_profiles()
        
        # Enhance each profile with extracted metadata
        enhanced_profiles = []
        for profile in profiles:
            try:
                # Get the full profile content
                profile_data = handler.profile_ops.get_profile(profile['id'])
                content = profile_data.get('content', '')
                
                # Extract metadata from content
                extracted_metadata = handler.extract_metadata_from_content(content)
                
                # Merge with existing profile data
                enhanced_profile = {**profile, **extracted_metadata}
                enhanced_profiles.append(enhanced_profile)
                
            except Exception as e:
                print(f"Error processing profile {profile.get('id', 'unknown')}: {str(e)}")
                # Add profile with default metadata if extraction fails
                enhanced_profile = {**profile, 'industry': 'Unknown', 'size': 'Unknown', 'regions': [], 'completeness': 0}
                enhanced_profiles.append(enhanced_profile)
        
        return handler.success_response({
            'profiles': enhanced_profiles,
            'count': len(enhanced_profiles)
        })
        
    except Exception as e:
        print(f"Error listing profiles: {str(e)}")
        return handler.handle_error(f'Failed to list profiles: {str(e)}')