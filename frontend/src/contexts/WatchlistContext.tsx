import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import type { Movie } from "../api";
import {
  getWatchlist,
  addToWatchlist as addToStorage,
  removeFromWatchlist as removeFromStorage,
  isInWatchlist,
  getPassedMovies,
  addToPassedMovies as addToPassedStorage,
  removeFromPassedMovies as removeFromPassedStorage,
  type WatchlistItem,
} from "../lib/watchlist";

interface PassedMovieRecord {
  tmdbId: number;
  timestamp: number;
}

interface WatchlistContextValue {
  watchlist: WatchlistItem[];
  passedMovies: Set<number>;
  addMovie: (movie: Movie) => boolean;
  removeMovie: (tmdbId: number) => boolean;
  toggleMovie: (movie: Movie) => boolean;
  isInList: (tmdbId: number) => boolean;
  passMovie: (tmdbId: number) => boolean;
  unpassMovie: (tmdbId: number) => boolean;
  isMoviePassed: (tmdbId: number) => boolean;
  lastPassedMovie: PassedMovieRecord | null;
}

const WatchlistContext = createContext<WatchlistContextValue | null>(null);

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(() => getWatchlist());
  const [passedMovies, setPassedMovies] = useState<Set<number>>(() => getPassedMovies());
  const [lastPassedMovie, setLastPassedMovie] = useState<PassedMovieRecord | null>(null);

  const refresh = useCallback(() => {
    setWatchlist(getWatchlist());
    setPassedMovies(getPassedMovies());
  }, []);

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "moody-watchlist" || e.key === "moody-passed") {
        refresh();
      }
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [refresh]);

  const addMovie = useCallback((movie: Movie) => {
    const success = addToStorage(movie);
    refresh();
    return success;
  }, [refresh]);

  const removeMovie = useCallback((tmdbId: number) => {
    const success = removeFromStorage(tmdbId);
    refresh();
    return success;
  }, [refresh]);

  const toggleMovie = useCallback((movie: Movie) => {
    if (isInWatchlist(movie.tmdb_id)) {
      return removeMovie(movie.tmdb_id);
    }
    return addMovie(movie);
  }, [addMovie, removeMovie]);

  const isInList = useCallback((tmdbId: number) => {
    return isInWatchlist(tmdbId);
  }, []);

  const passMovie = useCallback((tmdbId: number) => {
    const success = addToPassedStorage(tmdbId);
    if (success) {
      setLastPassedMovie({ tmdbId, timestamp: Date.now() });
    }
    refresh();
    return success;
  }, [refresh]);

  const unpassMovie = useCallback((tmdbId: number) => {
    const success = removeFromPassedStorage(tmdbId);
    if (success) {
      setLastPassedMovie((prev) => (prev?.tmdbId === tmdbId ? null : prev));
    }
    refresh();
    return success;
  }, [refresh]);

  const isMoviePassedFn = useCallback((tmdbId: number) => {
    return passedMovies.has(tmdbId);
  }, [passedMovies]);

  const value: WatchlistContextValue = {
    watchlist,
    passedMovies,
    addMovie,
    removeMovie,
    toggleMovie,
    isInList,
    passMovie,
    unpassMovie,
    isMoviePassed: isMoviePassedFn,
    lastPassedMovie,
  };

  return (
    <WatchlistContext.Provider value={value}>
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist() {
  const context = useContext(WatchlistContext);
  if (!context) {
    throw new Error("useWatchlist must be used within a WatchlistProvider");
  }
  return context;
}
