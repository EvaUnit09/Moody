import { useEffect, useState, type FormEvent } from "react";

const PLACEHOLDERS = [
  "something slow and melancholic...",
  "a movie that feels like a rainy sunday...",
  "high energy, no thinking required...",
  "a heist that goes almost too smoothly...",
];

const PLACEHOLDER_INTERVAL_MS = 3200;

interface SearchBoxProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchBox({ onSearch, isLoading }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % PLACEHOLDERS.length);
    }, PLACEHOLDER_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      onSearch(trimmed);
    }
  }

  function handleChipClick(example: string) {
    setQuery(example);
    onSearch(example);
  }

  return (
    <form className="search-box" onSubmit={handleSubmit}>
      <div className="tag tag-outline search-box-tag">mood, not genre</div>

      <input
        type="text"
        className="search-box-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={PLACEHOLDERS[placeholderIdx]}
        disabled={isLoading}
      />

      <div className="search-box-row">
        <span className="text-muted search-box-hint">
          describe how you want to feel, in your own words
        </span>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? "Thinking..." : "Search"}
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </div>

      {!query && (
        <div className="search-box-chips">
          {PLACEHOLDERS.map((example) => {
            const label = example.replace(/\.\.\.$/, "");
            return (
              <button
                key={example}
                type="button"
                className="tag tag-outline search-box-chip"
                disabled={isLoading}
                onClick={() => handleChipClick(label)}
              >
                {label}
              </button>
            );
          })}
        </div>
      )}
    </form>
  );
}
