import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  console.log(`[RESTART-PROXY] Handler called: ${req.method} ${req.url}`);
  console.log(`[RESTART-PROXY] Body:`, req.body);
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { agent, token } = req.body;
  
  const supportedAgents = ['architect', 'security-architect', 'auditor', 'risk-assessment'];
  if (!supportedAgents.includes(agent)) {
    return res.status(400).json({ error: `Agent ${agent} not supported` });
  }

  if (!token) {
    return res.status(401).json({ error: 'JWT token required' });
  }

  try {
    // All agents have restart endpoint on their specific paths
    const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL || 'http://localhost:9001';
    const url = `${agentsUrl}/${agent}/restart`;
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    
    console.log(`[RESTART-PROXY] Agent: ${agent}`);
    console.log(`[RESTART-PROXY] URL: ${url}`);
    console.log(`[RESTART-PROXY] Headers:`, headers);
    console.log(`[RESTART-PROXY] Token length: ${token.length}`);
    
    const response = await fetch(url, {
      method: 'POST',
      headers
    });
    
    console.log(`[RESTART-PROXY] Response status: ${response.status}`);
    console.log(`[RESTART-PROXY] Response headers:`, Object.fromEntries(response.headers.entries()));
    
    if (response.ok) {
      const data = await response.json();
      // nosemgrep
      console.log(`[RESTART-PROXY] Success for ${agent}:`, data);
      res.status(200).json(data);
    } else {
      const errorText = await response.text();
      // nosemgrep
      console.log(`[RESTART-PROXY] Error for ${agent}: ${response.status} - ${errorText}`);
      res.status(response.status).json({ error: 'Restart failed', details: errorText, status: response.status, agent });
    }
  } catch (error) {
    // nosemgrep
    console.log(`[RESTART-PROXY] Exception for ${agent}:`, error);
    res.status(503).json({ error: 'Connection failed', agent });
  }
}