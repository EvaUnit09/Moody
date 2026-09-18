import type { MovieRecommendation } from "../api";
import { MovieCard } from "./MovieCard";
import { useWatchlist } from "../hooks/useWatchlist";

interface ResultsGridProps {
  results: MovieRecommendation[];
  currentQuery?: string;
  onMoreLikeThis?: (title: string, currentQuery: string) => void;
}

export function ResultsGrid({ results, currentQuery = "", onMoreLikeThis }: ResultsGridProps) {
  const { toggleMovie, isInList, passMovie, isMoviePassed } = useWatchlist();

  const visibleResults = results.filter((movie) => !isMoviePassed(movie.tmdb_id));

  if (visibleResults.length === 0) {
    return null;
  }

  const handleMoreLikeThis = onMoreLikeThis && currentQuery
    ? (title: string) => onMoreLikeThis(title, currentQuery)
    : undefined;

  return (
    <div className="results-grid">
      {visibleResults.map((movie) => (
        <MovieCard
          key={movie.tmdb_id}
          movie={movie}
          isInWatchlist={isInList(movie.tmdb_id)}
          onToggleWatchlist={toggleMovie}
          onPass={passMovie}
          showPassButton={true}
          onMoreLikeThis={handleMoreLikeThis}
        />
      ))}
    </div>
  );
}
