import { useEffect, useState } from "react";
import { getPopular, recommend, type Movie, type MovieRecommendation } from "./api";
import { SearchBox } from "./components/SearchBox";
import { ResultsGrid } from "./components/ResultsGrid";
import { SkeletonGrid } from "./components/SkeletonGrid";
import { PosterCarousel } from "./components/PosterCarousel";
import "./App.css";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [popularMovies, setPopularMovies] = useState<Movie[]>([]);

  useEffect(() => {
    getPopular()
      .then(setPopularMovies)
      .catch(() => setPopularMovies([]));
  }, []);

  async function handleSearch(searchQuery: string) {
    setQuery(searchQuery);
    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const movies = await recommend(searchQuery);
      setResults(movies);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-bg">
      <header className="nav app-header">
        <span className="app-logo-dot" />
        <span className="nav-brand">Moody</span>
      </header>

      <section className="hero">
        <SearchBox onSearch={handleSearch} isLoading={isLoading} />
      </section>

      {!hasSearched && <PosterCarousel movies={popularMovies} />}

      {hasSearched && (
        <section className="results-section">
          {!error && (
            <div className="results-heading">
              <h6 className="text-muted">matches for &ldquo;{query}&rdquo;</h6>
            </div>
          )}

          {error && <p className="error">{error}</p>}

          {isLoading && <SkeletonGrid />}

          {!isLoading && !error && results.length === 0 && (
            <p className="status">
              No matches found. Try describing it differently.
            </p>
          )}

          {!isLoading && !error && <ResultsGrid results={results} />}
        </section>
      )}
    </div>
  );
}

export default App;
