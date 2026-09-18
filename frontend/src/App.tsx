import { useEffect, useRef, useState } from "react";
import { getPopular, recommend, type Movie, type MovieRecommendation } from "./api";
import { readPopularCache, writePopularCache } from "./lib/popularCache";
import { getRecentMoods, addRecentMood, clearRecentMoods } from "./lib/recentMoods";
import { SearchBox } from "./components/SearchBox";
import { ResultsGrid } from "./components/ResultsGrid";
import { SkeletonGrid } from "./components/SkeletonGrid";
import { PosterCarousel } from "./components/PosterCarousel";
import { CarouselSkeleton } from "./components/CarouselSkeleton";
import { MoodChips } from "./components/MoodChips";
import { RecentChips } from "./components/RecentChips";
import { RecoveryPrompt } from "./components/RecoveryPrompt";
import { WatchlistDrawer } from "./components/WatchlistDrawer";
import { ShareButton } from "./components/ShareButton";
import { useWatchlist } from "./hooks/useWatchlist";
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
  const [isWatchlistOpen, setIsWatchlistOpen] = useState(false);
  const [recentMoods, setRecentMoods] = useState<string[]>(() => getRecentMoods());
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const { watchlist } = useWatchlist();

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

  function handleGoHome() {
    abortControllerRef.current?.abort();
    setQuery("");
    setResults([]);
    setError(null);
    setHasSearched(false);
    setRecentMoods(getRecentMoods());
    window.history.pushState(null, "", window.location.pathname);
  }

  function handleClearRecentMoods() {
    clearRecentMoods();
    setRecentMoods([]);
  }

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
      addRecentMood(searchQuery);
      setRecentMoods(getRecentMoods());
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
        <button type="button" className="nav-brand" onClick={handleGoHome}>
          <span className="app-logo-dot" />
          <span>Moody</span>
        </button>
        <button
          type="button"
          className="btn btn-secondary watchlist-button"
          onClick={() => setIsWatchlistOpen(true)}
          aria-label="Open watchlist"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 256 256"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M240,94c0,70-103.79,126.66-108.21,129a8,8,0,0,1-7.58,0C119.79,220.66,16,164,16,94A62.07,62.07,0,0,1,78,32c20.65,0,38.73,8.88,50,23.89C139.27,40.88,157.35,32,178,32A62.07,62.07,0,0,1,240,94Z" />
          </svg>
          <span>My List</span>
          {watchlist.length > 0 && (
            <span className="tag tag-accent">{watchlist.length}</span>
          )}
        </button>
      </header>

      <section className="hero">
        {!hasSearched && (
          <>
            <RecentChips
              recentMoods={recentMoods}
              onMoodSelect={handleSearch}
              onClearAll={handleClearRecentMoods}
              disabled={isLoading}
            />
            <MoodChips onMoodSelect={handleSearch} disabled={isLoading} />
          </>
        )}
        <SearchBox 
          onSearch={handleSearch} 
          isLoading={isLoading}
          value={query}
          onChange={setQuery}
        />
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
              <ShareButton query={query} />
            </div>
          )}

          {isLoading && <SkeletonGrid />}

          {!isLoading && (error || results.length === 0) && (
            <RecoveryPrompt onMoodSelect={handleSearch} />
          )}

          {!isLoading && !error && <ResultsGrid results={results} />}
        </section>
      )}

      <WatchlistDrawer
        isOpen={isWatchlistOpen}
        onClose={() => setIsWatchlistOpen(false)}
      />
    </div>
  );
}

export default App;
