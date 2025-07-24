"""
Lambda function to create organization profiles
"""
import json
import uuid
from shared.base_lambda import BaseLambda
from shared.profile_s3_operations import ProfileS3Operations

class CreateProfileLambda(BaseLambda):
    def __init__(self):
        super().__init__()
        # Use centralized S3 operations for organization profiles
        self.profile_ops = ProfileS3Operations(s3_client=self.s3, documents_bucket=self.documents_bucket)

def lambda_handler(event, context):
    """Create a new organization profile"""
    handler = CreateProfileLambda()
    
    try:
        # Handle CORS preflight
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return handler.handle_options()
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        profile_name = body.get('profile_name')
        profile_content = body.get('profile_content')
        metadata = body.get('metadata', {})
        
        if not profile_name or not profile_content:
            return handler.handle_error('profile_name and profile_content are required', 400)
        
        # Generate unique profile ID
        profile_id = str(uuid.uuid4())
        
        # Create profile using centralized operations (S3)
        profile_metadata = handler.profile_ops.create_profile(
            profile_id=profile_id,
            profile_name=profile_name,
            profile_content=profile_content,
            metadata=metadata
        )
        
        # Create profile record in DynamoDB using client API (avoids resource deepcopy issues)
        from datetime import datetime
        
        handler.dynamodb_client.put_item(
            TableName=handler.projects_table_name,
            Item={
                'id': {'S': str(profile_id)},
                'name': {'S': str(profile_name)},
                'type': {'S': 'organization_profile'},
                'created_at': {'S': datetime.utcnow().isoformat()},
                'updated_at': {'S': datetime.utcnow().isoformat()},
                'status': {'S': 'active'},
                's3_key': {'S': f"org-profiles/{profile_id}.md"}
            }
        )
        
        print(f"Profile created: {profile_id} - {profile_name}")
        
        return handler.success_response({
            'message': 'Profile created successfully',
            'profile': profile_metadata
        }, 201)
        
    except Exception as e:
        print(f"Error creating profile: {str(e)}")
        import traceback
        traceback.print_exc()
        return handler.handle_error(f'Failed to create profile: {str(e)}')