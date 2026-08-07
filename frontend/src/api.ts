const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Movie {
  tmdb_id: number;
  title: string;
  poster_path: string | null;
  year: number | null;
  vote_average: number | null;
  genres: string[];
}

export interface MovieRecommendation extends Movie {
  reason: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function recommend(
  query: string,
  signal?: AbortSignal,
): Promise<MovieRecommendation[]> {
  const data = await apiFetch<{ results: MovieRecommendation[] }>("/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal,
  });
  return data.results;
}

export async function getPopular(): Promise<Movie[]> {
  const data = await apiFetch<{ results: Movie[] }>("/popular");
  return data.results;
}
