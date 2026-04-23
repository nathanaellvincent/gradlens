/**
 * GradLens API client. Wraps the single /search endpoint.
 *
 * API base URL resolves from the `NEXT_PUBLIC_API_URL` env var (exposed to
 * the browser bundle), defaulting to the dev server on 127.0.0.1:8000.
 * In prod this points at the Fly.io deployment.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type SearchHit = {
  source: string;
  company: string;
  upstream_id: string;
  title: string;
  url: string;
  location: string;
  snippet: string;
  distance: number;
};

export type SearchResponse = {
  query: string;
  k: number;
  total: number;
  index_size: number;
  latency_ms: number;
  hits: SearchHit[];
};

export async function search(
  query: string,
  k: number = 10,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, k: String(k) });
  const res = await fetch(`${API_BASE_URL}/search?${params.toString()}`, {
    signal,
    headers: { accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`search failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SearchResponse;
}
