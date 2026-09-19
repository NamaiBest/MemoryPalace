// Server-side only. DEMO_TOKEN must never reach the browser, so nothing here may be
// imported from a client component — the API routes under app/api proxy on its behalf.
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8771";
const TOKEN = process.env.DEMO_TOKEN ?? "";

export function backendHeaders(): HeadersInit {
  return TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
}

export async function backendFetch(path: string, init?: RequestInit) {
  return fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: { ...backendHeaders(), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
}
