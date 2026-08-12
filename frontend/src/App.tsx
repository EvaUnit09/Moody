import { useEffect, useRef, useState } from "react";
import { getPopular, recommend, type Movie, type MovieRecommendation } from "./api";
import { readPopularCache, writePopularCache } from "./lib/popularCache";
import { SearchBox } from "./components/SearchBox";
import { ResultsGrid } from "./components/ResultsGrid";
import { SkeletonGrid } from "./components/SkeletonGrid";
import { PosterCarousel } from "./components/PosterCarousel";
import { CarouselSkeleton } from "./components/CarouselSkeleton";
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
  const [popularMovies, setPopularMovies] = useState<Movie[]>(
    () => readPopularCache() ?? [],
  );
  const [isPopularLoading, setIsPopularLoading] = useState(
    () => readPopularCache() === null,
  );
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const hadCachedMovies = readPopularCache() !== null;
    getPopular()
      .then((movies) => {
        setPopularMovies(movies);
        writePopularCache(movies);
      })
      .catch(() => {
        if (!hadCachedMovies) setPopularMovies([]);
      })
      .finally(() => setIsPopularLoading(false));
  }, []);

  useEffect(() => {
    const initialQuery = new URLSearchParams(window.location.search).get("q");
    if (initialQuery) {
      handleSearch(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSearch(searchQuery: string) {
    setQuery(searchQuery);
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    window.history.pushState(null, "", `?q=${encodeURIComponent(searchQuery)}`);

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const requestId = ++requestIdRef.current;

    try {
      const movies = await recommend(searchQuery, controller.signal);
      if (requestIdRef.current !== requestId) return;
      setResults(movies);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (requestIdRef.current !== requestId) return;
      setError(getErrorMessage(err));
      setResults([]);
    } finally {
      if (requestIdRef.current === requestId) {
        setIsLoading(false);
      }
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

      {!hasSearched && isPopularLoading && <CarouselSkeleton />}
      {!hasSearched && !isPopularLoading && (
        <PosterCarousel movies={popularMovies} />
      )}

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
