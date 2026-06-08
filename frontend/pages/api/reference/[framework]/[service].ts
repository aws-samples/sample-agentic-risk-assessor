import type { NextApiRequest, NextApiResponse } from 'next';
import { validatePathParam } from '../../../../utils/validatePathParam';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { framework, service } = req.query;
  if (!framework || !service) {
    return res.status(400).json({ error: 'Missing framework or service' });
  }

  let validFramework: string;
  let validService: string;
  try {
    validFramework = validatePathParam(framework as string, 'framework');
    validService = validatePathParam(service as string, 'service');
  } catch {
    return res.status(400).json({ error: 'Invalid framework or service parameter' });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';

  try {
    const response = await fetch(`${apiUrl}/api/reference/${validFramework}/${validService}`);
    const body = await response.text();

    if (!response.ok) {
      return res.status(response.status).send(body);
    }

    res.setHeader('Content-Type', 'text/html');
    res.status(200).send(body);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
}
