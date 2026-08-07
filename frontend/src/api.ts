const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface MovieRecommendation {
  tmdb_id: number;
  title: string;
  poster_path: string | null;
  reason: string;
}

export async function recommend(query: string): Promise<MovieRecommendation[]> {
  const response = await fetch(`${API_URL}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  return data.results;
}
