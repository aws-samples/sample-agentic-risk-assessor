import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Sidebar from '../../components/Sidebar';
import markdownStyles from '../../styles/markdownContent.module.css';

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

export default function OrganizationProfileDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [profile, setProfile] = useState<OrganizationProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      const { getJwtToken } = await import('../../utils/auth');
      const token = await getJwtToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch(`/api/profiles/${profileId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch profile: ${response.statusText}`);
      }
      
      const data = await response.json();
      
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

  const handleEdit = () => {
    router.push(`/organization-profiles/${id}/edit`);
  };

  const handleDelete = async () => {
    if (!profile) return;
    
    const confirmed = confirm(`Are you sure you want to delete "${profile.name}"? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      // TODO: Replace with actual API call to delete_profile Lambda
      // const response = await fetch(`/api/organization-profiles/${id}`, {
      //   method: 'DELETE'
      // });
      // if (!response.ok) throw new Error('Failed to delete profile');
      
      router.push('/organization-profiles');
    } catch (err) {
      console.error('Error deleting profile:', err);
      setError('Failed to delete profile. Please try again.');
    }
  };

  const handleUseForAssessment = () => {
    // Navigate to risk assessment with this profile selected
    router.push(`/risk-assessment?profile=${id}`);
  };

  const getCompletenessColor = (completeness: number) => {
    if (completeness >= 80) return '#28a745';
    if (completeness >= 60) return '#ffc107';
    return '#dc3545';
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
      <div style={{ flex: 1, padding: '1rem', overflow: 'auto' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          {/* Header */}
          <div style={{ 
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: '2rem',
            paddingBottom: '1rem',
            borderBottom: '2px solid #ff6b35'
          }}>
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                marginBottom: '1rem'
              }}>
                <button
                  onClick={() => router.push('/organization-profiles')}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#6c757d',
                    fontSize: '1.5rem',
                    cursor: 'pointer',
                    padding: '0.25rem'
                  }}
                  title="Back to Organization Profiles"
                >
                  ←
                </button>
                <h1 style={{
                  fontSize: '2rem',
                  fontWeight: '600',
                  color: '#ff6b35',
                  margin: 0
                }}>
                  {profile.name}
                </h1>
              </div>
              
              <div style={{
                display: 'flex',
                gap: '2rem',
                alignItems: 'center',
                marginLeft: '3rem',
                flexWrap: 'wrap'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>Industry:</span>
                  <span style={{ fontWeight: '600' }}>{profile.metadata.industry}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>Size:</span>
                  <span style={{ fontWeight: '600' }}>{profile.metadata.size}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>Regions:</span>
                  <span style={{ fontWeight: '600' }}>{profile.metadata.regions.join(', ')}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>Completeness:</span>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <div style={{
                      width: '60px',
                      height: '8px',
                      backgroundColor: '#e9ecef',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${profile.metadata.completeness}%`,
                        height: '100%',
                        backgroundColor: getCompletenessColor(profile.metadata.completeness),
                        transition: 'width 0.3s'
                      }} />
                    </div>
                    <span style={{
                      fontSize: '0.9rem',
                      color: getCompletenessColor(profile.metadata.completeness),
                      fontWeight: '600'
                    }}>
                      {profile.metadata.completeness}%
                    </span>
                  </div>
                </div>
              </div>
              
              <div style={{
                marginTop: '0.5rem',
                marginLeft: '3rem',
                fontSize: '0.9rem',
                color: '#6c757d'
              }}>
                Created {new Date(profile.createdAt).toLocaleDateString()} • 
                Last updated {new Date(profile.updatedAt).toLocaleDateString()}
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
              <button
                onClick={handleUseForAssessment}
                style={{
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1rem',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Use for Assessment
              </button>
              <button
                onClick={handleEdit}
                style={{
                  backgroundColor: '#ff6b35',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1rem',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Edit Profile
              </button>
              <button
                onClick={handleDelete}
                style={{
                  backgroundColor: 'transparent',
                  color: '#dc3545',
                  border: '1px solid #dc3545',
                  padding: '0.75rem 1rem',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
            </div>
          </div>

          {/* Profile Content */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e9ecef',
            borderRadius: '8px',
            padding: '2rem',
            minHeight: '600px'
          }}>
            {profile.content ? (
              <div className={markdownStyles['markdown-content']}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {profile.content}
                </ReactMarkdown>
              </div>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '3rem',
                color: '#6c757d'
              }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📝</div>
                <h3>No Content Available</h3>
                <p>This profile doesn't have detailed content yet.</p>
                <button
                  onClick={handleEdit}
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
                  Add Content
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}