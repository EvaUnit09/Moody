import type { Movie } from "../api";

const WATCHLIST_KEY = "moody-watchlist";
const PASSED_KEY = "moody-passed";

export interface WatchlistItem extends Movie {
  addedAt: number;
}

function isValidMovie(item: unknown): item is Movie {
  if (typeof item !== "object" || item === null) return false;
  const obj = item as Record<string, unknown>;
  return (
    typeof obj.tmdb_id === "number" &&
    typeof obj.title === "string" &&
    (obj.poster_path === null || typeof obj.poster_path === "string") &&
    (obj.year === null || typeof obj.year === "number") &&
    (obj.vote_average === null || typeof obj.vote_average === "number") &&
    Array.isArray(obj.genres) &&
    obj.genres.every((g) => typeof g === "string")
  );
}

function isValidWatchlistItem(item: unknown): item is WatchlistItem {
  if (!isValidMovie(item)) return false;
  const obj = item as Record<string, unknown>;
  return typeof obj.addedAt === "number";
}

function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (error) {
    if (error instanceof Error && error.name === "QuotaExceededError") {
      console.warn("localStorage quota exceeded. Watchlist changes not saved.");
      return false;
    }
    console.error("Failed to save to localStorage:", error);
    return false;
  }
}

export function getWatchlist(): WatchlistItem[] {
  try {
    const stored = localStorage.getItem(WATCHLIST_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isValidWatchlistItem);
  } catch {
    return [];
  }
}

export function addToWatchlist(movie: Movie): void {
  if (!isValidMovie(movie)) {
    console.error("Invalid movie data, not adding to watchlist");
    return;
  }
  const watchlist = getWatchlist();
  const exists = watchlist.some((item) => item.tmdb_id === movie.tmdb_id);
  if (!exists) {
    const item: WatchlistItem = { ...movie, addedAt: Date.now() };
    watchlist.unshift(item);
    safeSetItem(WATCHLIST_KEY, JSON.stringify(watchlist));
  }
}

export function removeFromWatchlist(tmdbId: number): void {
  const watchlist = getWatchlist();
  const filtered = watchlist.filter((item) => item.tmdb_id !== tmdbId);
  safeSetItem(WATCHLIST_KEY, JSON.stringify(filtered));
}

export function isInWatchlist(tmdbId: number): boolean {
  const watchlist = getWatchlist();
  return watchlist.some((item) => item.tmdb_id === tmdbId);
}

export function getPassedMovies(): Set<number> {
  try {
    const stored = localStorage.getItem(PASSED_KEY);
    if (!stored) return new Set();
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((id) => typeof id === "number"));
  } catch {
    return new Set();
  }
}

export function addToPassedMovies(tmdbId: number): void {
  const passed = getPassedMovies();
  passed.add(tmdbId);
  safeSetItem(PASSED_KEY, JSON.stringify([...passed]));
}

export function removeFromPassedMovies(tmdbId: number): void {
  const passed = getPassedMovies();
  passed.delete(tmdbId);
  safeSetItem(PASSED_KEY, JSON.stringify([...passed]));
}

export function isMoviePassed(tmdbId: number): boolean {
  return getPassedMovies().has(tmdbId);
}

export function exportWatchlist(): string {
  const watchlist = getWatchlist();
  return JSON.stringify(watchlist, null, 2);
}

export function exportWatchlistAsText(): string {
  const watchlist = getWatchlist();
  return watchlist
    .map((movie) => {
      const year = movie.year ? ` (${movie.year})` : "";
      const rating = movie.vote_average ? ` - ${movie.vote_average.toFixed(1)}/10` : "";
      return `${movie.title}${year}${rating}`;
    })
    .join("\n");
}
