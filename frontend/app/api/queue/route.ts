import { proxyToBackend } from '@/lib/backend';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { search } = new URL(request.url);
  return proxyToBackend(`/api/queue${search}`);
}
