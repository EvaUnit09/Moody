import type { Movie } from "../api";

const WATCHLIST_KEY = "moody-watchlist";
const PASSED_KEY = "moody-passed";

export interface WatchlistItem extends Movie {
  addedAt: number;
}

export function getWatchlist(): WatchlistItem[] {
  try {
    const stored = localStorage.getItem(WATCHLIST_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function addToWatchlist(movie: Movie): void {
  const watchlist = getWatchlist();
  const exists = watchlist.some((item) => item.tmdb_id === movie.tmdb_id);
  if (!exists) {
    const item: WatchlistItem = { ...movie, addedAt: Date.now() };
    watchlist.unshift(item);
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(watchlist));
  }
}

export function removeFromWatchlist(tmdbId: number): void {
  const watchlist = getWatchlist();
  const filtered = watchlist.filter((item) => item.tmdb_id !== tmdbId);
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(filtered));
}

export function isInWatchlist(tmdbId: number): boolean {
  const watchlist = getWatchlist();
  return watchlist.some((item) => item.tmdb_id === tmdbId);
}

export function getPassedMovies(): Set<number> {
  try {
    const stored = localStorage.getItem(PASSED_KEY);
    return new Set(stored ? JSON.parse(stored) : []);
  } catch {
    return new Set();
  }
}

export function addToPassedMovies(tmdbId: number): void {
  const passed = getPassedMovies();
  passed.add(tmdbId);
  localStorage.setItem(PASSED_KEY, JSON.stringify([...passed]));
}

export function removeFromPassedMovies(tmdbId: number): void {
  const passed = getPassedMovies();
  passed.delete(tmdbId);
  localStorage.setItem(PASSED_KEY, JSON.stringify([...passed]));
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
