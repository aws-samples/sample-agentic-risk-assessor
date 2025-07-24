import { useRouter } from 'next/router';
import RiskList from '../components/RiskList';
import Sidebar from '../components/Sidebar';

export default function Risks() {
  const router = useRouter();
  
  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#d0d0d0',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '2rem', overflow: 'auto' }}>
        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: 'bold',
          color: '#ff6b35',
          marginBottom: '2rem',
          textAlign: 'center'
        }}>
          Risk Assessments
        </h1>
        
        <div style={{
          backgroundColor: '#ffffff',
          border: '2px solid #ff6b35',
          borderRadius: '8px',
          padding: '2rem'
        }}>
          <RiskList />
        </div>
      </div>
    </div>
  );
}