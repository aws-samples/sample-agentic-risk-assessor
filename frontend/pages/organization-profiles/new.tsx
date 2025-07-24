import { useState } from 'react';
import { useRouter } from 'next/router';
import Sidebar from '../../components/Sidebar';
import VoiceInteractiveProfileBuilder from '../../components/VoiceInteractiveProfileBuilder';

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

export default function NewOrganizationProfile() {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);

  const handleProfileComplete = async (profile: OrganizationProfile) => {
    try {
      setIsCreating(true);
      
      // TODO: Replace with actual API call to save the profile
      console.log('Profile created:', profile);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate to the new profile's detail page
      router.push(`/organization-profiles/${profile.id}`);
    } catch (error) {
      console.error('Error saving profile:', error);
      // Handle error - could show a toast notification
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancel = () => {
    if (confirm('Are you sure you want to cancel? Any progress will be lost.')) {
      router.push('/organization-profiles');
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
              alignItems: 'center',
              gap: '1rem',
              marginBottom: '0.5rem'
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
                fontSize: '1.8rem',
                fontWeight: '600',
                color: '#ff6b35',
                margin: 0
              }}>
                Create New Organization Profile
              </h1>
            </div>
            <p style={{
              fontSize: '1rem',
              color: '#666',
              margin: 0,
              marginLeft: '3rem'
            }}>
              Let's build a comprehensive profile for your organization through an interactive conversation
            </p>
          </div>

          {/* Conversational Profile Builder */}
          <div style={{ 
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0
          }}>
            {isCreating ? (
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                backgroundColor: '#ffffff',
                border: '2px solid #ff6b35',
                borderRadius: '8px',
                padding: '3rem'
              }}>
                <div style={{
                  fontSize: '3rem',
                  marginBottom: '1rem',
                  animation: 'spin 2s linear infinite'
                }}>
                  ⚙️
                </div>
                <h2 style={{
                  color: '#ff6b35',
                  marginBottom: '1rem'
                }}>
                  Creating Your Profile...
                </h2>
                <p style={{
                  color: '#6c757d',
                  textAlign: 'center',
                  maxWidth: '400px'
                }}>
                  We're processing your responses and generating your organization profile. 
                  This will just take a moment.
                </p>
                <style jsx>{`
                  @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}</style>
              </div>
            ) : (
              <VoiceInteractiveProfileBuilder
                onProfileComplete={handleProfileComplete}
                onCancel={handleCancel}
                profileId="new-profile"
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
            <h4 style={{
              margin: '0 0 0.5rem 0',
              fontSize: '0.9rem',
              color: '#495057',
              fontWeight: '600'
            }}>
              💡 Tips for creating a great profile:
            </h4>
            <ul style={{
              margin: 0,
              paddingLeft: '1.5rem',
              fontSize: '0.85rem',
              color: '#6c757d'
            }}>
              <li>Be specific about your industry and regulatory requirements</li>
              <li>Include details about your technology stack and infrastructure</li>
              <li>Mention any existing security tools or frameworks you use</li>
              <li>Describe your risk tolerance and business priorities</li>
              <li>You can always edit and refine your profile later</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}