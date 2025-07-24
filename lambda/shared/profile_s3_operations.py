"""
S3 operations module for organization profiles
Provides centralized S3 operations for org-profiles/ prefix in documents bucket
"""
import json
import boto3
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

PROFILE_PREFIX = 'org-profiles/'

class ProfileS3Operations:
    """Centralized S3 operations for organization profiles"""
    
    def __init__(self, s3_client=None, documents_bucket=None):
        """
        Initialize S3 operations for organization profiles
        
        Args:
            s3_client: Optional S3 client, will create one if not provided
            documents_bucket: Optional bucket name, will get from env if not provided
        """
        self.s3 = s3_client or boto3.client('s3')
        self.documents_bucket = documents_bucket or os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents-development')
    
    def create_profile(self, profile_id: str, profile_name: str, profile_content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new organization profile
        
        Args:
            profile_id: Unique identifier for the profile
            profile_name: Human-readable name for the profile
            profile_content: Markdown content of the profile
            metadata: Additional metadata for the profile
            
        Returns:
            Dict containing the created profile metadata
            
        Raises:
            Exception: If profile creation fails
        """
        try:
            # Create profile metadata
            profile_metadata = {
                'id': profile_id,
                'name': profile_name,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'file_path': f"{PROFILE_PREFIX}{profile_id}.md",
                **(metadata or {})
            }
            
            # Save profile content to S3
            self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}{profile_id}.md",
                Body=profile_content,
                ContentType='text/markdown'
            )
            
            # Update metadata index
            self._update_metadata_index(profile_metadata, operation='create')
            
            return profile_metadata
            
        except Exception as e:
            raise Exception(f"Failed to create profile {profile_id}: {str(e)}")
    
    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Get organization profile content and metadata
        
        Args:
            profile_id: Unique identifier for the profile
            
        Returns:
            Dict containing profile content and metadata
            
        Raises:
            Exception: If profile not found or retrieval fails
        """
        try:
            # Get profile content from S3
            try:
                response = self.s3.get_object(
                    Bucket=self.documents_bucket,
                    Key=f"{PROFILE_PREFIX}{profile_id}.md"
                )
                profile_content = response['Body'].read().decode('utf-8')
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise Exception(f"Profile {profile_id} not found")
                raise e
            
            # Get profile metadata
            profile_metadata = self._get_profile_metadata(profile_id)
            
            return {
                'profile_id': profile_id,
                'content': profile_content,
                'metadata': profile_metadata
            }
            
        except Exception as e:
            raise Exception(f"Failed to get profile {profile_id}: {str(e)}")
    
    def update_profile(self, profile_id: str, profile_content: str, metadata_updates: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update an existing organization profile
        
        Args:
            profile_id: Unique identifier for the profile
            profile_content: Updated markdown content
            metadata_updates: Updates to profile metadata
            
        Returns:
            Dict containing updated profile metadata
            
        Raises:
            Exception: If profile not found or update fails
        """
        try:
            # Check if profile exists
            try:
                self.s3.head_object(
                    Bucket=self.documents_bucket,
                    Key=f"{PROFILE_PREFIX}{profile_id}.md"
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise Exception(f"Profile {profile_id} not found")
                raise e
            
            # Update profile content
            self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}{profile_id}.md",
                Body=profile_content,
                ContentType='text/markdown'
            )
            
            # Update metadata
            updated_metadata = self._update_metadata_index(
                {'id': profile_id, 'updated_at': datetime.utcnow().isoformat(), **(metadata_updates or {})},
                operation='update'
            )
            
            return updated_metadata
            
        except Exception as e:
            raise Exception(f"Failed to update profile {profile_id}: {str(e)}")
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all available organization profiles
        
        Returns:
            List of profile metadata dictionaries
            
        Raises:
            Exception: If listing fails
        """
        try:
            # Get metadata index
            try:
                response = self.s3.get_object(
                    Bucket=self.documents_bucket,
                    Key=f"{PROFILE_PREFIX}metadata.json"
                )
                metadata_index = json.loads(response['Body'].read().decode('utf-8'))
                profiles = metadata_index.get('profiles', [])
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    # If metadata doesn't exist, scan S3 for profile files
                    profiles = self._scan_s3_for_profiles()
                else:
                    raise e
            
            # Sort profiles by updated_at (most recent first)
            profiles.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            
            return profiles
            
        except Exception as e:
            raise Exception(f"Failed to list profiles: {str(e)}")
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete an organization profile
        
        Args:
            profile_id: Unique identifier for the profile
            
        Returns:
            True if deletion was successful
            
        Raises:
            Exception: If profile not found or deletion fails
        """
        try:
            # Check if profile exists
            try:
                self.s3.head_object(
                    Bucket=self.documents_bucket,
                    Key=f"{PROFILE_PREFIX}{profile_id}.md"
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise Exception(f"Profile {profile_id} not found")
                raise e
            
            # Delete profile content from S3
            self.s3.delete_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}{profile_id}.md"
            )
            
            # Update metadata index
            self._update_metadata_index({'id': profile_id}, operation='delete')
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete profile {profile_id}: {str(e)}")
    
    def profile_exists(self, profile_id: str) -> bool:
        """
        Check if a profile exists
        
        Args:
            profile_id: Unique identifier for the profile
            
        Returns:
            True if profile exists, False otherwise
        """
        try:
            self.s3.head_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}{profile_id}.md"
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise e
    
    def _get_profile_metadata(self, profile_id: str) -> Dict[str, Any]:
        """Get metadata for a specific profile"""
        try:
            response = self.s3.get_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}metadata.json"
            )
            metadata_index = json.loads(response['Body'].read().decode('utf-8'))
            
            # Find the profile metadata
            for profile in metadata_index['profiles']:
                if profile['id'] == profile_id:
                    return profile
                    
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise e
        
        # If metadata doesn't exist or profile not found, create basic metadata
        return {
            'id': profile_id,
            'name': 'Unknown Profile',
            'file_path': f"{PROFILE_PREFIX}{profile_id}.md"
        }
    
    def _update_metadata_index(self, profile_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Update the metadata index file"""
        try:
            # Get existing metadata
            try:
                response = self.s3.get_object(
                    Bucket=self.documents_bucket,
                    Key=f"{PROFILE_PREFIX}metadata.json"
                )
                metadata_index = json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    metadata_index = {'profiles': []}
                else:
                    raise e
            
            profile_id = profile_data['id']
            
            if operation == 'create':
                # Add new profile to metadata
                metadata_index['profiles'].append(profile_data)
                updated_profile = profile_data
                
            elif operation == 'update':
                # Find and update existing profile
                updated_profile = None
                for profile in metadata_index['profiles']:
                    if profile['id'] == profile_id:
                        profile.update(profile_data)
                        updated_profile = profile
                        break
                
                if not updated_profile:
                    # Profile not found in metadata, create it
                    updated_profile = {
                        'id': profile_id,
                        'name': profile_data.get('name', 'Unknown Profile'),
                        'created_at': datetime.utcnow().isoformat(),
                        'file_path': f"{PROFILE_PREFIX}{profile_id}.md",
                        **profile_data
                    }
                    metadata_index['profiles'].append(updated_profile)
                    
            elif operation == 'delete':
                # Remove profile from metadata
                metadata_index['profiles'] = [
                    profile for profile in metadata_index['profiles']
                    if profile['id'] != profile_id
                ]
                updated_profile = None
            
            # Save updated metadata
            self.s3.put_object(
                Bucket=self.documents_bucket,
                Key=f"{PROFILE_PREFIX}metadata.json",
                Body=json.dumps(metadata_index, indent=2),
                ContentType='application/json'
            )
            
            return updated_profile
            
        except Exception as e:
            raise Exception(f"Failed to update metadata index: {str(e)}")
    
    def _scan_s3_for_profiles(self) -> List[Dict[str, Any]]:
        """Scan S3 for profile files when metadata doesn't exist"""
        profiles = []
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.documents_bucket,
                Prefix=PROFILE_PREFIX
            )
            
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.md') and key != f"{PROFILE_PREFIX}metadata.json":
                    profile_id = key.replace(PROFILE_PREFIX, '').replace('.md', '')
                    profiles.append({
                        'id': profile_id,
                        'name': f'Profile {profile_id}',
                        'file_path': key,
                        'created_at': obj['LastModified'].isoformat(),
                        'updated_at': obj['LastModified'].isoformat()
                    })
        except Exception as e:
            print(f"Error scanning S3 for profiles: {str(e)}")
        
        return profiles