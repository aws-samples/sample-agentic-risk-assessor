import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { agent, token } = req.body;
  
  const supportedAgents = ['architect', 'security-architect', 'auditor', 'risk-assessment'];
  if (!supportedAgents.includes(agent)) {
    return res.status(400).json({ error: `Agent ${agent} not supported` });
  }

  try {
    // Map agent names to their specific health endpoints
    const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
    if (!agentsUrl) {
      return res.status(500).json({ error: 'NEXT_PUBLIC_AGENTS_URL environment variable not configured' });
    }
    const baseUrl = agentsUrl.startsWith('http') ? agentsUrl : `http://${agentsUrl}`;
    const agentEndpoints = {
      'architect': `${baseUrl}/architect/health`,
      'security-architect': `${baseUrl}/security-architect/health`,
      'auditor': `${baseUrl}/auditor/health`,
      'risk-assessment': `${baseUrl}/risk-assessment/health`
    };
    
    const endpoint = agentEndpoints[agent as keyof typeof agentEndpoints];
    if (!endpoint) {
      return res.status(400).json({ error: `No health endpoint for agent ${agent}` });
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(endpoint, { 
      method: 'GET',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.status === 200) {
      res.status(200).json({ status: 'online', agent });
    } else {
      res.status(503).json({ status: 'offline', agent });
    }
  } catch (error) {
    res.status(503).json({ status: 'offline', agent });
  }
}