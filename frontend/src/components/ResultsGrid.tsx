import { useCallback } from "react";
import type { Movie, MovieRecommendation } from "../api";
import { MovieCard } from "./MovieCard";
import { useWatchlist } from "../hooks/useWatchlist";
import { useToast } from "../contexts/ToastContext";

interface ResultsGridProps {
  results: MovieRecommendation[];
}

export function ResultsGrid({ results }: ResultsGridProps) {
  const { toggleMovie, isInList, passMovie, unpassMovie, isMoviePassed } = useWatchlist();
  const { showToast } = useToast();

  const handlePass = useCallback((tmdbId: number) => {
    passMovie(tmdbId);
    showToast("Hidden", {
      action: {
        label: "Undo",
        onClick: () => {
          unpassMovie(tmdbId);
        },
      },
      duration: 6000,
    });
  }, [passMovie, unpassMovie, showToast]);

  const handleToggleWatchlist = useCallback((movie: Movie) => {
    const wasInList = isInList(movie.tmdb_id);
    toggleMovie(movie);
    
    if (wasInList) {
      showToast("Removed from watchlist", { duration: 2000 });
    } else {
      showToast("Added to watchlist", { duration: 2000 });
    }
  }, [toggleMovie, isInList, showToast]);

  const visibleResults = results.filter((movie) => !isMoviePassed(movie.tmdb_id));

  if (visibleResults.length === 0) {
    return null;
  }

  return (
    <div className="results-grid">
      {visibleResults.map((movie) => (
        <MovieCard
          key={movie.tmdb_id}
          movie={movie}
          isInWatchlist={isInList(movie.tmdb_id)}
          onToggleWatchlist={handleToggleWatchlist}
          onPass={handlePass}
          showPassButton={true}
        />
      ))}
    </div>
  );
}
