import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Handle preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { token } = req.body;

  if (!token) {
    return res.status(401).json({ error: 'JWT token required' });
  }

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.risk-agent.com';
    const url = `${apiUrl}/restart-system`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const data = await response.json();
      res.status(200).json(data);
    } else {
      const errorText = await response.text();
      res.status(response.status).json({ 
        error: 'System restart failed', 
        details: errorText, 
        status: response.status 
      });
    }
  } catch (error) {
    console.error('System restart error:', error);
    res.status(503).json({ error: 'Connection failed' });
  }
}