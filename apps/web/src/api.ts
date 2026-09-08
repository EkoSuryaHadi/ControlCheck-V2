export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, options);
  if (!response.ok) {
    let message = `Permintaan gagal (${response.status}).`;
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch { /* Keep HTTP status if the server does not return JSON. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export function json(body: unknown): RequestInit {
  return { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) };
}

