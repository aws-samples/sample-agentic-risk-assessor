import { NextApiRequest, NextApiResponse } from 'next';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method } = req;

  // Get authorization token from request headers
  const authToken = req.headers.authorization;
  if (!authToken) {
    return res.status(401).json({ error: 'Authorization token required' });
  }

  try {
    switch (method) {
      case 'GET':
        // List all organization profiles
        const listResponse = await fetch(`${API_BASE_URL}/api/profiles`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken,
          },
        });

        if (!listResponse.ok) {
          throw new Error(`Failed to fetch profiles: ${listResponse.statusText}`);
        }

        const listData = await listResponse.json();
        res.status(200).json(listData);
        break;

      case 'POST':
        // Create new organization profile
        const createResponse = await fetch(`${API_BASE_URL}/api/profiles`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken,
          },
          body: JSON.stringify(req.body),
        });

        if (!createResponse.ok) {
          throw new Error(`Failed to create profile: ${createResponse.statusText}`);
        }

        const createData = await createResponse.json();
        res.status(201).json(createData);
        break;

      default:
        res.setHeader('Allow', ['GET', 'POST']);
        res.status(405).end(`Method ${method} Not Allowed`);
    }
  } catch (error) {
    console.error('API Error:', error);
    res.status(500).json({ 
      error: 'Internal Server Error', 
      message: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
}