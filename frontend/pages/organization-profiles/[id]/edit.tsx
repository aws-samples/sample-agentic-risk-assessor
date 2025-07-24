import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Sidebar from '../../../components/Sidebar';
import ProfileEditor from '../../../components/ProfileEditor';
import VoiceInteractiveProfileBuilder from '../../../components/VoiceInteractiveProfileBuilder';
import { getJwtToken } from '../../../utils/auth';

interface OrganizationProfile {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  filePath: string;
  content?: string;
  metadata: {
    industry: string;
    size: string;
    regions: string[];
    completeness: number;
  };
}

export default function EditOrganizationProfile() {
  const router = useRouter();
  const { id } = router.query;
  const [profile, setProfile] = useState<OrganizationProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<'editor' | 'conversation'>('editor');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (id) {
      fetchProfile(id as string);
    }
  }, [id]);

  const fetchProfile = async (profileId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Get JWT token for authentication
      const token = await getJwtToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      
      console.log('Fetching profile with ID:', profileId);
      
      const response = await fetch(`/api/profiles/${profileId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response body:', errorText);
        console.error('Full error details:', {
          status: response.status,
          statusText: response.statusText,
          url: response.url,
          body: errorText
        });
        throw new Error(`Failed to fetch profile: ${response.statusText} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Profile data received:', data);
      
      // Transform the API response to match our interface
      const transformedProfile: OrganizationProfile = {
        id: data.metadata.id,
        name: data.metadata.name,
        createdAt: new Date(data.metadata.created_at || new Date()),
        updatedAt: new Date(data.metadata.updated_at || new Date()),
        filePath: data.metadata.file_path,
        content: data.content || '',
        metadata: {
          industry: data.metadata.industry || 'Unknown',
          size: data.metadata.size || 'Unknown',
          regions: data.metadata.regions || [],
          completeness: data.metadata.completeness || 0
        }
      };
      
      setProfile(transformedProfile);
    } catch (err) {
      console.error('Error fetching profile:', err);
      setError('Failed to load organization profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (content: string) => {
    if (!profile) return;
    
    try {
      setIsSaving(true);
      
      // Get JWT token for authentication
      const token = await getJwtToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch(`/api/organization-profiles/${id}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          profile_content: content,
          profile_name: profile.name 
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to save profile');
      }
      
      // Update local state
      setProfile(prev => prev ? { ...prev, content, updatedAt: new Date() } : null);
      
      console.log('Profile saved successfully');
    } catch (err) {
      console.error('Error saving profile:', err);
      throw new Error('Failed to save profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleProfileComplete = async (updatedProfile: OrganizationProfile) => {
    try {
      setIsSaving(true);
      
      // TODO: Replace with actual API call to update the profile
      console.log('Profile updated via conversation:', updatedProfile);
      
      // Update local state
      setProfile(updatedProfile);
      
      // Switch back to editor mode to show the updated content
      setEditMode('editor');
    } catch (error) {
      console.error('Error updating profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    router.push(`/organization-profiles/${id}`);
  };

  if (loading) {
    return (
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#e4e4e4',
        color: '#000000',
        lineHeight: 1.6,
        height: '100vh',
        display: 'flex'
      }}>
        <Sidebar activePage="organization-profiles" />
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center' 
        }}>
          <div style={{ textAlign: 'center', color: '#6c757d' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⏳</div>
            <h2>Loading Profile...</h2>
          </div>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#e4e4e4',
        color: '#000000',
        lineHeight: 1.6,
        height: '100vh',
        display: 'flex'
      }}>
        <Sidebar activePage="organization-profiles" />
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center' 
        }}>
          <div style={{ 
            textAlign: 'center',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            padding: '2rem',
            borderRadius: '8px',
            border: '1px solid #f5c6cb'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
            <h2>Profile Not Found</h2>
            <p>{error || 'The requested organization profile could not be found.'}</p>
            <button
              onClick={() => router.push('/organization-profiles')}
              style={{
                backgroundColor: '#ff6b35',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '4px',
                cursor: 'pointer',
                marginTop: '1rem'
              }}
            >
              Back to Profiles
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="organization-profiles" />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem', overflow: 'hidden' }}>
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto',
          height: '100%',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Header */}
          <div style={{ 
            marginBottom: '1rem',
            paddingBottom: '1rem',
            borderBottom: '1px solid #e9ecef'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.5rem'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem'
              }}>
                <button
                  onClick={() => router.push(`/organization-profiles/${id}`)}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#6c757d',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    padding: '0.25rem'
                  }}
                  title="Back to Profile"
                >
                  ←
                </button>
                <h1 style={{
                  fontSize: '1.8rem',
                  fontWeight: '600',
                  color: '#ff6b35',
                  margin: 0
                }}>
                  Edit: {profile.name}
                </h1>
              </div>

              {/* Mode Toggle */}
              <div style={{
                display: 'flex',
                backgroundColor: '#f8f9fa',
                border: '1px solid #e9ecef',
                borderRadius: '6px',
                overflow: 'hidden'
              }}>
                <button
                  onClick={() => setEditMode('editor')}
                  style={{
                    backgroundColor: editMode === 'editor' ? '#ff6b35' : 'transparent',
                    color: editMode === 'editor' ? 'white' : '#6c757d',
                    border: 'none',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    fontWeight: editMode === 'editor' ? '600' : 'normal'
                  }}
                >
                  📝 Direct Edit
                </button>
                <button
                  onClick={() => setEditMode('conversation')}
                  style={{
                    backgroundColor: editMode === 'conversation' ? '#ff6b35' : 'transparent',
                    color: editMode === 'conversation' ? 'white' : '#6c757d',
                    border: 'none',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    fontWeight: editMode === 'conversation' ? '600' : 'normal'
                  }}
                >
                  💬 Conversation
                </button>
              </div>
            </div>
            
            <p style={{
              fontSize: '1rem',
              color: '#666',
              margin: 0,
              marginLeft: '3rem'
            }}>
              {editMode === 'editor' 
                ? 'Edit the profile content directly using markdown format'
                : 'Update your profile through an interactive conversation'
              }
            </p>
          </div>

          {/* Editor Content */}
          <div style={{ 
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0
          }}>
            {editMode === 'editor' ? (
              <ProfileEditor
                profileContent={profile.content || ''}
                onSave={handleSave}
                profileName={profile.name}
              />
            ) : (
              <VoiceInteractiveProfileBuilder
                existingProfile={profile}
                onProfileComplete={handleProfileComplete}
                onCancel={() => setEditMode('editor')}
                profileId={profile.id}
                enableVoice={true}
              />
            )}
          </div>

          {/* Help Text */}
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #e9ecef'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '2rem'
            }}>
              <div style={{ flex: 1 }}>
                <h4 style={{
                  margin: '0 0 0.5rem 0',
                  fontSize: '0.9rem',
                  color: '#495057',
                  fontWeight: '600'
                }}>
                  {editMode === 'editor' ? '📝 Editor Mode:' : '💬 Conversation Mode:'}
                </h4>
                <p style={{
                  margin: 0,
                  fontSize: '0.85rem',
                  color: '#6c757d'
                }}>
                  {editMode === 'editor' 
                    ? 'Use markdown syntax to format your content. The preview shows how it will appear.'
                    : 'Chat with the AI to update your profile. It will ask questions to help refine the content.'
                  }
                </p>
              </div>
              
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                alignItems: 'center'
              }}>
                <button
                  onClick={() => router.push(`/organization-profiles/${id}`)}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#6c757d',
                    border: '1px solid #6c757d',
                    borderRadius: '4px',
                    padding: '0.5rem 1rem',
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => router.push(`/organization-profiles/${id}`)}
                  style={{
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '0.5rem 1rem',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    fontWeight: '600'
                  }}
                >
                  View Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}