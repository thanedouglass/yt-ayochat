const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';
const BACKEND_API_KEY = process.env.BACKEND_API_KEY;

/** Proxy a PWA request to the FastAPI backend, attaching the server-only API key. */
export async function proxyToBackend(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_API_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(BACKEND_API_KEY ? { 'X-API-Key': BACKEND_API_KEY } : {}),
        ...init.headers,
      },
      cache: 'no-store',
    });
  } catch (error) {
    return Response.json(
      { detail: `Backend unreachable: ${error instanceof Error ? error.message : 'unknown error'}` },
      { status: 502 }
    );
  }

  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: { 'Content-Type': upstream.headers.get('Content-Type') || 'application/json' },
  });
}
