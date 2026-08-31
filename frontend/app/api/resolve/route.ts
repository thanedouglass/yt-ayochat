import { proxyToBackend } from '@/lib/backend';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const body = await request.text();
  return proxyToBackend('/api/resolve', { method: 'POST', body });
}
