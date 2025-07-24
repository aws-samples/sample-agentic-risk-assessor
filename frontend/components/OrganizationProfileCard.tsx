import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

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

interface OrganizationProfileCardProps {
  profiles?: OrganizationProfile[];
  onCreateNew?: () => void;
  onViewProfile?: (profileId: string) => void;
  onEditProfile?: (profileId: string) => void;
}

export default function OrganizationProfileCard({
  profiles = [],
  onCreateNew,
  onViewProfile,
  onEditProfile
}: OrganizationProfileCardProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [profileData, setProfileData] = useState<OrganizationProfile[]>([]);

  useEffect(() => {
    setProfileData(profiles);
    setIsLoading(false);
  }, [profiles.length]);

  const handleCreateNew = () => {
    if (onCreateNew) {
      onCreateNew();
    } else {
      // Default navigation to organization profiles page
      router.push('/organization-profiles/new');
    }
  };

  const handleViewProfile = (profileId: string) => {
    if (onViewProfile) {
      onViewProfile(profileId);
    } else {
      router.push(`/organization-profiles/${profileId}`);
    }
  };

  const handleEditProfile = (profileId: string) => {
    if (onEditProfile) {
      onEditProfile(profileId);
    } else {
      router.push(`/organization-profiles/${profileId}/edit`);
    }
  };

  const getProfileSummary = () => {
    if (profileData.length === 0) {
      return "No organization profiles created yet";
    }
    
    const activeProfiles = profileData.length;
    const avgCompleteness = profileData.reduce((sum, profile) => sum + profile.metadata.completeness, 0) / profileData.length;
    
    return `${activeProfiles} profile${activeProfiles !== 1 ? 's' : ''} • ${Math.round(avgCompleteness)}% avg completion`;
  };

  const getRecentProfile = () => {
    if (profileData.length === 0) return null;
    
    return profileData.reduce((latest, profile) => 
      new Date(profile.updatedAt) > new Date(latest.updatedAt) ? profile : latest
    );
  };

  const recentProfile = getRecentProfile();

  return (
    <div 
      style={{
        backgroundColor: '#ffffff',
        border: '2px solid #ff6b35',
        borderRadius: '8px',
        padding: '1rem',
        cursor: 'pointer',
        transition: 'transform 0.2s',
        textAlign: 'center'
      }}
      onClick={() => router.push('/organization-profiles')}
      onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
      onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
    >
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏢</div>
      
      <h3 style={{ 
        color: '#ff6b35', 
        marginBottom: '0.5rem', 
        fontSize: '1.3rem' 
      }}>
        Organization Profiles
      </h3>
      
      <p style={{ 
        color: '#666', 
        fontSize: '0.95rem',
        marginBottom: '1rem'
      }}>
        {isLoading ? 'Loading profiles...' : getProfileSummary()}
      </p>

      {recentProfile && (
        <div style={{
          backgroundColor: '#f8f9fa',
          border: '1px solid #e9ecef',
          borderRadius: '4px',
          padding: '0.75rem',
          marginBottom: '1rem',
          textAlign: 'left'
        }}>
          <div style={{
            fontSize: '0.9rem',
            fontWeight: '600',
            color: '#495057',
            marginBottom: '0.25rem'
          }}>
            Recent: {recentProfile.name}
          </div>
          <div style={{
            fontSize: '0.8rem',
            color: '#6c757d'
          }}>
            {recentProfile.metadata.industry} • {recentProfile.metadata.completeness}% complete
          </div>
        </div>
      )}

      <div style={{
        display: 'flex',
        gap: '0.5rem',
        justifyContent: 'center',
        marginTop: '1rem'
      }}>
        <button
          style={{
            backgroundColor: '#ff6b35',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            padding: '0.5rem 1rem',
            fontSize: '0.9rem',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}
          onClick={(e) => {
            e.stopPropagation();
            handleCreateNew();
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e55a2b'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#ff6b35'}
        >
          Create New
        </button>
        
        {profileData.length > 0 && (
          <button
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
            onClick={(e) => {
              e.stopPropagation();
              router.push('/organization-profiles');
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
            View All
          </button>
        )}
      </div>
    </div>
  );
}