import { useState } from "react";
import { recommend, type MovieRecommendation } from "./api";
import { SearchBox } from "./components/SearchBox";
import { ResultsGrid } from "./components/ResultsGrid";
import "./App.css";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

function App() {
  const [results, setResults] = useState<MovieRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch(query: string) {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const movies = await recommend(query);
      setResults(movies);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>What do you want to watch?</h1>
      <p className="tagline">
        Describe a mood or scenario. Skip the genre dropdowns.
      </p>

      <SearchBox onSearch={handleSearch} isLoading={isLoading} />

      {error && <p className="error">{error}</p>}

      {isLoading && <p className="status">Finding picks for you...</p>}

      {!isLoading && !error && hasSearched && results.length === 0 && (
        <p className="status">No matches found. Try describing it differently.</p>
      )}

      <ResultsGrid results={results} />
    </div>
  );
}

export default App;
