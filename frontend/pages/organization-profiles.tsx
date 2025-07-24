import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Sidebar from '../components/Sidebar';
import ProfileSelector from '../components/ProfileSelector';
import { getJwtToken } from '../utils/auth';

interface OrganizationProfile {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  filePath: string;
  metadata: {
    industry: string;
    size: string;
    regions: string[];
    completeness: number;
  };
}

export default function OrganizationProfiles() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<OrganizationProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<string>('');

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get JWT token for authentication
      const token = await getJwtToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch('/api/profiles', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch profiles: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Transform the API response to match our interface
      const transformedProfiles: OrganizationProfile[] = (data.profiles || []).map((profile: any) => ({
        id: profile.id,
        name: profile.name,
        createdAt: new Date(profile.created_at),
        updatedAt: new Date(profile.updated_at),
        filePath: profile.file_path,
        metadata: {
          industry: profile.industry || 'Unknown',
          size: profile.size || 'Unknown',
          regions: profile.regions || [],
          completeness: profile.completeness || 0
        }
      }));
      
      setProfiles(transformedProfiles);
    } catch (err) {
      console.error('Error fetching organization profiles:', err);
      setError('Failed to load organization profiles. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProfile = (profileId: string) => {
    setSelectedProfile(profileId);
    router.push(`/organization-profiles/${profileId}`);
  };

  const handleCreateNew = () => {
    router.push('/organization-profiles/new');
  };

  const handleEditProfile = (profileId: string) => {
    router.push(`/organization-profiles/${profileId}/edit`);
  };

  const handleDeleteProfile = async (profileId: string) => {
    try {
      // Get JWT token for authentication
      const token = await getJwtToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch(`/api/organization-profiles/${profileId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete profile');
      }
      
      // Remove from local state
      setProfiles(prev => prev.filter(p => p.id !== profileId));
      
      // Clear selection if deleted profile was selected
      if (selectedProfile === profileId) {
        setSelectedProfile('');
      }
    } catch (err) {
      console.error('Error deleting profile:', err);
      setError('Failed to delete profile. Please try again.');
    }
  };

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
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          {/* Header */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '2rem'
          }}>
            <div>
              <h1 style={{
                fontSize: '2rem',
                fontWeight: '600',
                color: '#ff6b35',
                margin: 0,
                marginBottom: '0.5rem'
              }}>
                Organization Profiles
              </h1>
              <p style={{
                fontSize: '1.1rem',
                color: '#666',
                margin: 0
              }}>
                Manage organization profiles for tailored security recommendations
              </p>
            </div>
            
            <button
              onClick={handleCreateNew}
              style={{
                backgroundColor: '#ff6b35',
                color: '#ffffff',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e55a2b'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#ff6b35'}
            >
              <span>➕</span>
              Create New Profile
            </button>
          </div>

          {/* Profile Selector */}
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            overflow: 'hidden',
            minHeight: 'calc(100vh - 200px)'
          }}>
            <ProfileSelector
              profiles={profiles}
              selectedProfile={selectedProfile}
              onSelect={handleSelectProfile}
              onCreateNew={handleCreateNew}
              onEdit={handleEditProfile}
              onDelete={handleDeleteProfile}
              loading={loading}
              error={error}
              showActions={true}
            />
          </div>

          {/* Quick Actions */}
          {profiles.length > 0 && (
            <div style={{
              marginTop: '2rem',
              padding: '1rem',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px',
              border: '1px solid #e9ecef'
            }}>
              <h3 style={{
                margin: '0 0 1rem 0',
                fontSize: '1.1rem',
                color: '#495057'
              }}>
                Quick Actions
              </h3>
              <div style={{
                display: 'flex',
                gap: '1rem',
                flexWrap: 'wrap'
              }}>
                <button
                  onClick={() => router.push('/organization-profiles/compare')}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#ff6b35',
                    border: '1px solid #ff6b35',
                    borderRadius: '4px',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#ff6b35';
                    e.currentTarget.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#ff6b35';
                  }}
                >
                  Compare Profiles
                </button>
                <button
                  onClick={() => router.push('/organization-profiles/templates')}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#6c757d',
                    border: '1px solid #6c757d',
                    borderRadius: '4px',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#6c757d';
                    e.currentTarget.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#6c757d';
                  }}
                >
                  Browse Templates
                </button>
                <button
                  onClick={() => {
                    const csvContent = profiles.map(p => 
                      `"${p.name}","${p.metadata.industry}","${p.metadata.size}","${p.metadata.regions.join(';')}","${p.metadata.completeness}%","${new Date(p.updatedAt).toLocaleDateString()}"`
                    ).join('\n');
                    const blob = new Blob([`Name,Industry,Size,Regions,Completeness,Last Updated\n${csvContent}`], { type: 'text/csv' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'organization-profiles.csv';
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#28a745',
                    border: '1px solid #28a745',
                    borderRadius: '4px',
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#28a745';
                    e.currentTarget.style.color = 'white';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#28a745';
                  }}
                >
                  Export CSV
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}