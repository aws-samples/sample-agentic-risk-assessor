import { useState, useEffect } from 'react';
import axios from 'axios';

interface Risk {
  id: string;
  name: string;
  description: string;
  risk_level: string;
  factors: string[];
}

export default function RiskList() {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRisks = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/risks');
        setRisks(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch risk assessments');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRisks();
  }, []);

  if (loading) return <div>Loading risk assessments...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Risk Assessments</h2>
      {risks.length === 0 ? (
        <p>No risk assessments found.</p>
      ) : (
        <ul>
          {risks.map((risk) => (
            <li key={risk.id}>
              <h3>{risk.name}</h3>
              <p>{risk.description}</p>
              <p>Risk Level: {risk.risk_level}</p>
              <p>Factors: {risk.factors.join(', ')}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}