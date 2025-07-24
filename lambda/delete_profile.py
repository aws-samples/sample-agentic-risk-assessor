"""
Lambda function to delete organization profiles
"""
import json
from shared.base_lambda import BaseLambda
from shared.profile_s3_operations import ProfileS3Operations

class DeleteProfileLambda(BaseLambda):
    def __init__(self):
        super().__init__()
        # Use centralized S3 operations for organization profiles
        self.profile_ops = ProfileS3Operations(s3_client=self.s3, documents_bucket=self.documents_bucket)

def lambda_handler(event, context):
    """Delete an organization profile"""
    handler = DeleteProfileLambda()
    
    try:
        # Handle CORS preflight
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return handler.handle_options()
        
        # Get profile ID from path parameters
        profile_id = event.get('pathParameters', {}).get('id')
        if not profile_id:
            return handler.handle_error('Profile ID is required', 400)
        
        # Delete profile using centralized operations
        try:
            handler.profile_ops.delete_profile(profile_id)
            
            return handler.success_response({
                'message': 'Profile deleted successfully',
                'profile_id': profile_id
            })
            
        except Exception as e:
            if "not found" in str(e).lower():
                return handler.handle_error('Profile not found', 404)
            raise e
        
    except Exception as e:
        print(f"Error deleting profile: {str(e)}")
        return handler.handle_error(f'Failed to delete profile: {str(e)}')