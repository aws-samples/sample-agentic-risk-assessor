"""
Lambda function to update organization profiles
"""
import json
from shared.base_lambda import BaseLambda
from shared.profile_s3_operations import ProfileS3Operations

class UpdateProfileLambda(BaseLambda):
    def __init__(self):
        super().__init__()
        # Use centralized S3 operations for organization profiles
        self.profile_ops = ProfileS3Operations(s3_client=self.s3, documents_bucket=self.documents_bucket)

def lambda_handler(event, context):
    """Update an existing organization profile"""
    handler = UpdateProfileLambda()
    
    try:
        # Handle CORS preflight
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return handler.handle_options()
        
        # Get profile ID from path parameters
        profile_id = event.get('pathParameters', {}).get('id')
        if not profile_id:
            return handler.handle_error('Profile ID is required', 400)
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        profile_content = body.get('profile_content')
        metadata_updates = body.get('metadata', {})
        
        if not profile_content:
            return handler.handle_error('profile_content is required', 400)
        
        # Update profile using centralized operations
        try:
            updated_metadata = handler.profile_ops.update_profile(
                profile_id=profile_id,
                profile_content=profile_content,
                metadata_updates=metadata_updates
            )
            
            return handler.success_response({
                'message': 'Profile updated successfully',
                'profile_id': profile_id,
                'metadata': updated_metadata
            })
            
        except Exception as e:
            if "not found" in str(e).lower():
                return handler.handle_error('Profile not found', 404)
            raise e
        
    except Exception as e:
        print(f"Error updating profile: {str(e)}")
        return handler.handle_error(f'Failed to update profile: {str(e)}')