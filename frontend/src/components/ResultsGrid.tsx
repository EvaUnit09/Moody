import type { MovieRecommendation } from "../api";
import { MovieCard } from "./MovieCard";

interface ResultsGridProps {
  results: MovieRecommendation[];
}

export function ResultsGrid({ results }: ResultsGridProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <div className="results-grid">
      {results.map((movie) => (
        <MovieCard key={movie.tmdb_id} movie={movie} />
      ))}
    </div>
  );
}
