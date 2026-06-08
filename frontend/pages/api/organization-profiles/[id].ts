import { NextApiRequest, NextApiResponse } from 'next';
import { validatePathParam } from '../../../utils/validatePathParam';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { method, query } = req;
  const rawId = query.id;

  if (!rawId || typeof rawId !== 'string') {
    return res.status(400).json({ error: 'Profile ID is required' });
  }

  let id: string;
  try {
    id = validatePathParam(rawId, 'Profile ID');
  } catch {
    return res.status(400).json({ error: 'Invalid Profile ID format' });
  }

  // Get authorization token from request headers
  const authToken = req.headers.authorization;
  if (!authToken) {
    return res.status(401).json({ error: 'Authorization token required' });
  }

  try {
    switch (method) {
      case 'GET':
        // Get specific organization profile
        const getResponse = await fetch(`${API_BASE_URL}/api/profiles/${id}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken,
          },
        });

        if (!getResponse.ok) {
          throw new Error(`Failed to fetch profile: ${getResponse.statusText}`);
        }

        const getData = await getResponse.json();
        res.status(200).json(getData);
        break;

      case 'PUT':
        // Update organization profile
        const updateResponse = await fetch(`${API_BASE_URL}/api/profiles/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken,
          },
          body: JSON.stringify(req.body),
        });

        if (!updateResponse.ok) {
          throw new Error(`Failed to update profile: ${updateResponse.statusText}`);
        }

        const updateData = await updateResponse.json();
        res.status(200).json(updateData);
        break;

      case 'DELETE':
        // Delete organization profile
        const deleteResponse = await fetch(`${API_BASE_URL}/api/profiles/${id}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken,
          },
        });

        if (!deleteResponse.ok) {
          throw new Error(`Failed to delete profile: ${deleteResponse.statusText}`);
        }

        const deleteData = await deleteResponse.json();
        res.status(200).json(deleteData);
        break;

      default:
        res.setHeader('Allow', ['GET', 'PUT', 'DELETE']);
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