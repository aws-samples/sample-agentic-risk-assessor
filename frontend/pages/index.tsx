import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import Sidebar from '../components/Sidebar';
import OrganizationProfileCard from '../components/OrganizationProfileCard';

export default function Home() {
  const [message, setMessage] = useState('Loading...');
  const router = useRouter();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/health');
        setMessage(response.data.message || 'System operational');
      } catch (error) {
        setMessage('Error connecting to backend');
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, []);

  const handleMenuClick = (action: string) => {
    if (action === 'Create new project') {
      router.push('/new-project');
    } else if (action === 'View Projects') {
      router.push('/projects');
    } else {
      alert(`${action} clicked. This feature will be implemented soon.`);
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
      <Sidebar activePage="dashboard" />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '2rem', overflow: 'auto' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{
            fontSize: '2rem',
            fontWeight: '600',
            color: '#ff6b35',
            textAlign: 'center'
          }}>
            Welcome to Risk Assessor
          </div>

          <div style={{
            fontSize: '1.2rem',
            color: '#666',
            textAlign: 'center',
            marginBottom: '2rem'
          }}>
            AI-powered security and risk assessment agentic platform
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 0.5fr))',
            gridTemplateRows: 'minmax(100px, auto)',
            justifyContent: 'center',
            gap: '2rem',
            marginBottom: '2rem'
          }}>
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
              onClick={() => router.push('/new-project')}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>➕</div>
              <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '1.3rem' }}>Create New Project</h3>
              <p style={{ color: '#666', fontSize: '0.95rem' }}>Start a new risk assessment project with AI-powered analysis</p>
            </div>
            
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
              onClick={() => router.push('/projects')}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
              <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '1.3rem' }}>View Projects</h3>
              <p style={{ color: '#666', fontSize: '0.95rem' }}>Review and manage your existing risk assessment projects</p>
            </div>
            
            <OrganizationProfileCard />
            
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
              onClick={() => router.push('/risk-assessment')}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
              <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '1.3rem' }}>Risk Assessment</h3>
              <p style={{ color: '#666', fontSize: '0.95rem' }}>Interactive risk assessment with specialized AI agents</p>
            </div>
            
            {/* <div 
              style={{
                backgroundColor: '#ffffff',
                border: '2px solid #ff6b35',
                borderRadius: '8px',
                padding: '1rem',
                cursor: 'pointer',
                transition: 'transform 0.2s',
                textAlign: 'center'
              }}
              onClick={() => router.push('/agents')}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤖</div>
              <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '1.3rem' }}>Chat with Agents</h3>
              <p style={{ color: '#666', fontSize: '0.95rem' }}>Interact directly with specialized AI security agents</p>
            </div> */}
          </div>

          <div 
            style={{
              backgroundColor: '#ffffff',
              border: '2px solid #ff6b35',
              borderRadius: '8px',
              padding: '1rem',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'transform 0.2s'
            }}
            onClick={() => router.push('/health')}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ color: '#ff6b35',fontSize: '1.2rem', fontWeight: 600, marginBottom: '1rem' }}>System Status</div>
            <div style={{ color: message?.includes('Error') ? '#dc3545' : '#28a745', fontSize: '1.5rem' }}>{message}</div>
            <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '0.5rem' }}>Click to view detailed agent status</div>
          </div>
        </div>
      </div>
    </div>
  );
}