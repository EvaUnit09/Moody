import type { Movie } from "../api";

export const POPULAR_CACHE_STORAGE_KEY = "movierec:popular-cache";
export const POPULAR_CACHE_STALE_MS = 10 * 60 * 1000;

interface CachedPopular {
  movies: Movie[];
  storedAt: number;
}

function isCachedPopular(value: unknown): value is CachedPopular {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return Array.isArray(candidate.movies) && typeof candidate.storedAt === "number";
}

export function readPopularCache(): Movie[] | null {
  try {
    const raw = window.localStorage.getItem(POPULAR_CACHE_STORAGE_KEY);
    if (raw === null) return null;

    const parsed: unknown = JSON.parse(raw);
    if (!isCachedPopular(parsed)) return null;

    const isStale = Date.now() - parsed.storedAt > POPULAR_CACHE_STALE_MS;
    return isStale ? null : parsed.movies;
  } catch {
    return null;
  }
}

export function writePopularCache(movies: Movie[]): void {
  try {
    const entry: CachedPopular = { movies, storedAt: Date.now() };
    window.localStorage.setItem(POPULAR_CACHE_STORAGE_KEY, JSON.stringify(entry));
  } catch {
    // localStorage can throw (private browsing, quota) — caching is best-effort.
  }
}
