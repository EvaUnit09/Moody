import { useState, useCallback, useEffect } from "react";
import type { Movie } from "../api";
import {
  getWatchlist,
  addToWatchlist as addToStorage,
  removeFromWatchlist as removeFromStorage,
  isInWatchlist,
  type WatchlistItem,
} from "../lib/watchlist";

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(() => getWatchlist());

  const refresh = useCallback(() => {
    setWatchlist(getWatchlist());
  }, []);

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "moody-watchlist") {
        refresh();
      }
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [refresh]);

  const addMovie = useCallback((movie: Movie) => {
    addToStorage(movie);
    refresh();
  }, [refresh]);

  const removeMovie = useCallback((tmdbId: number) => {
    removeFromStorage(tmdbId);
    refresh();
  }, [refresh]);

  const toggleMovie = useCallback((movie: Movie) => {
    if (isInWatchlist(movie.tmdb_id)) {
      removeMovie(movie.tmdb_id);
    } else {
      addMovie(movie);
    }
  }, [addMovie, removeMovie]);

  const isInList = useCallback((tmdbId: number) => {
    return isInWatchlist(tmdbId);
  }, []);

  return {
    watchlist,
    addMovie,
    removeMovie,
    toggleMovie,
    isInList,
  };
}
