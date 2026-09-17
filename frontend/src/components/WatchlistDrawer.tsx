import { useWatchlist } from "../hooks/useWatchlist";
import { MovieCard } from "./MovieCard";
import { exportWatchlist, exportWatchlistAsText } from "../lib/watchlist";

interface WatchlistDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function WatchlistDrawer({ isOpen, onClose }: WatchlistDrawerProps) {
  const { watchlist, toggleMovie, isInList } = useWatchlist();

  const handleExportJSON = () => {
    const data = exportWatchlist();
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moody-watchlist-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportText = () => {
    const data = exportWatchlistAsText();
    const blob = new Blob([data], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moody-watchlist-${new Date().toISOString().split("T")[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <h3 className="drawer-title">My List</h3>
          <button
            type="button"
            className="btn btn-icon"
            onClick={onClose}
            aria-label="Close watchlist"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 256 256"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M205.66,194.34a8,8,0,0,1-11.32,11.32L128,139.31,61.66,205.66a8,8,0,0,1-11.32-11.32L116.69,128,50.34,61.66A8,8,0,0,1,61.66,50.34L128,116.69l66.34-66.35a8,8,0,0,1,11.32,11.32L139.31,128Z" />
            </svg>
          </button>
        </div>

        {watchlist.length === 0 ? (
          <div className="drawer-empty">
            <p className="text-muted">Your watchlist is empty.</p>
            <p className="text-muted">
              Add movies by clicking the heart icon on any result card.
            </p>
          </div>
        ) : (
          <>
            <div className="drawer-actions">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleExportJSON}
              >
                Export JSON
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleExportText}
              >
                Export Text
              </button>
              <span className="drawer-count">
                {watchlist.length} {watchlist.length === 1 ? "movie" : "movies"}
              </span>
            </div>
            <div className="drawer-grid">
              {watchlist.map((movie) => (
                <MovieCard
                  key={movie.tmdb_id}
                  movie={movie}
                  isInWatchlist={isInList(movie.tmdb_id)}
                  onToggleWatchlist={toggleMovie}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}
