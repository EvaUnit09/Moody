import { useMemo, useState } from "react";
import type { MovieRecommendation } from "../api";
import { MovieCard } from "./MovieCard";
import { useWatchlist } from "../hooks/useWatchlist";
import { SortPills, type SortOption } from "./SortPills";

interface ResultsGridProps {
  results: MovieRecommendation[];
}

function sortMovies(movies: MovieRecommendation[], sortOption: SortOption): MovieRecommendation[] {
  const sorted = [...movies];
  
  switch (sortOption) {
    case "best-match":
      return sorted;
    case "highest-rated":
      return sorted.sort((a, b) => {
        const ratingA = a.vote_average ?? -1;
        const ratingB = b.vote_average ?? -1;
        return ratingB - ratingA;
      });
    case "newest":
      return sorted.sort((a, b) => {
        const yearA = a.year ?? -1;
        const yearB = b.year ?? -1;
        return yearB - yearA;
      });
    case "title-az":
      return sorted.sort((a, b) => a.title.localeCompare(b.title));
    default:
      return sorted;
  }
}

export function ResultsGrid({ results }: ResultsGridProps) {
  const { toggleMovie, isInList, passMovie, isMoviePassed } = useWatchlist();
  const [sortOption, setSortOption] = useState<SortOption>("best-match");

  const sortedResults = useMemo(() => {
    return sortMovies(results, sortOption);
  }, [results, sortOption]);

  const visibleResults = sortedResults.filter((movie) => !isMoviePassed(movie.tmdb_id));

  if (visibleResults.length === 0) {
    return null;
  }

  return (
    <>
      <SortPills selectedSort={sortOption} onSortChange={setSortOption} />
      <div className="results-grid">
        {visibleResults.map((movie) => (
          <MovieCard
            key={movie.tmdb_id}
            movie={movie}
            isInWatchlist={isInList(movie.tmdb_id)}
            onToggleWatchlist={toggleMovie}
            onPass={passMovie}
            showPassButton={true}
          />
        ))}
      </div>
    </>
  );
}
