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

interface WatchlistContextValue {
  watchlist: WatchlistItem[];
  passedMovies: Set<number>;
  addMovie: (movie: Movie) => void;
  removeMovie: (tmdbId: number) => void;
  toggleMovie: (movie: Movie) => void;
  isInList: (tmdbId: number) => boolean;
  passMovie: (tmdbId: number) => void;
  unpassMovie: (tmdbId: number) => void;
  isMoviePassed: (tmdbId: number) => boolean;
}

const WatchlistContext = createContext<WatchlistContextValue | null>(null);

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(() => getWatchlist());
  const [passedMovies, setPassedMovies] = useState<Set<number>>(() => getPassedMovies());

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

  const passMovie = useCallback((tmdbId: number) => {
    addToPassedStorage(tmdbId);
    refresh();
  }, [refresh]);

  const unpassMovie = useCallback((tmdbId: number) => {
    removeFromPassedStorage(tmdbId);
    refresh();
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
