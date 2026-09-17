import type { MovieRecommendation } from "../api";
import { MovieCard } from "./MovieCard";
import { useWatchlist } from "../hooks/useWatchlist";
import { addToPassedMovies, isMoviePassed } from "../lib/watchlist";

interface ResultsGridProps {
  results: MovieRecommendation[];
}

export function ResultsGrid({ results }: ResultsGridProps) {
  const { toggleMovie, isInList } = useWatchlist();

  const handlePass = (tmdbId: number) => {
    addToPassedMovies(tmdbId);
  };

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
          onToggleWatchlist={toggleMovie}
          onPass={handlePass}
          showPassButton={true}
        />
      ))}
    </div>
  );
}
