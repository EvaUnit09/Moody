import { useState } from "react";
import type { Movie, WatchProvider } from "../api";

const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342";
const MAX_GENRE_TAGS = 2;

interface MovieCardProps {
  movie: Movie & { reason?: string; providers?: WatchProvider[] };
  isInWatchlist?: boolean;
  onToggleWatchlist?: (movie: Movie) => void;
  onPass?: (tmdbId: number) => void;
  showPassButton?: boolean;
  onMoreLikeThis?: (title: string) => void;
}

export function MovieCard({ 
  movie, 
  isInWatchlist = false, 
  onToggleWatchlist,
  onPass,
  showPassButton = false,
  onMoreLikeThis,
}: MovieCardProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const posterClassName = `movie-card-poster${isLoaded ? " movie-card-poster-loaded" : ""}`;
  const providers = movie.providers || [];

  const handleToggleWatchlist = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onToggleWatchlist?.(movie);
  };

  const handlePass = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onPass?.(movie.tmdb_id);
  };

  const handleMoreLikeThis = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onMoreLikeThis?.(movie.title);
  };

  return (
    <div className="card elev-sm movie-card">
      <a
        href={`https://www.themoviedb.org/movie/${movie.tmdb_id}`}
        target="_blank"
        rel="noopener noreferrer"
        className="movie-card-poster-link"
      >
        {movie.poster_path ? (
          <img
            src={`${POSTER_BASE_URL}${movie.poster_path}`}
            alt={`${movie.title} poster`}
            loading="lazy"
            onLoad={() => setIsLoaded(true)}
            className={posterClassName}
          />
        ) : (
          <div className="movie-card-poster movie-card-poster-placeholder">
            No poster
          </div>
        )}
      </a>
      <div className="movie-card-body">
        {movie.year && <div className="card-kicker">{movie.year}</div>}
        <div className="card-title">{movie.title}</div>
        {movie.genres.length > 0 && (
          <div className="movie-card-genres">
            {movie.genres.slice(0, MAX_GENRE_TAGS).map((genre) => (
              <span key={genre} className="tag tag-neutral">
                {genre}
              </span>
            ))}
          </div>
        )}
        {movie.reason && <p className="card-body">{movie.reason}</p>}
        {providers.length > 0 && (
          <div className="movie-card-providers">
            {providers.map((provider, index) => (
              <a
                key={index}
                href={provider.link}
                target="_blank"
                rel="noopener noreferrer"
                className="provider-logo-link"
                title={`Watch on ${provider.name}`}
              >
                {provider.logo_url ? (
                  <img
                    src={provider.logo_url}
                    alt={provider.name}
                    className="provider-logo"
                  />
                ) : (
                  <span className="provider-name">{provider.name}</span>
                )}
              </a>
            ))}
          </div>
        )}
        {movie.vote_average != null && (
          <div className="card-meta movie-card-meta">
            <span>
              TMDB <strong>{movie.vote_average.toFixed(1)}</strong>
            </span>
          </div>
        )}
        {(onMoreLikeThis || onToggleWatchlist || (showPassButton && onPass)) && (
          <div className="movie-card-actions">
            {onMoreLikeThis && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={handleMoreLikeThis}
                aria-label="Find more like this"
                title="Find more like this"
              >
                More like this
              </button>
            )}
            {onToggleWatchlist && (
              <button
                type="button"
                className="btn btn-ghost btn-icon"
                onClick={handleToggleWatchlist}
                aria-label={isInWatchlist ? "Remove from watchlist" : "Add to watchlist"}
                title={isInWatchlist ? "Remove from watchlist" : "Add to watchlist"}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 256 256"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  {isInWatchlist ? (
                    <path d="M240,94c0,70-103.79,126.66-108.21,129a8,8,0,0,1-7.58,0C119.79,220.66,16,164,16,94A62.07,62.07,0,0,1,78,32c20.65,0,38.73,8.88,50,23.89C139.27,40.88,157.35,32,178,32A62.07,62.07,0,0,1,240,94Z" />
                  ) : (
                    <path d="M178,32c-20.65,0-38.73,8.88-50,23.89C116.73,40.88,98.65,32,78,32A62.07,62.07,0,0,0,16,94c0,70,103.79,126.66,108.21,129a8,8,0,0,0,7.58,0C136.21,220.66,240,164,240,94A62.07,62.07,0,0,0,178,32ZM128,206.8C109.74,196.16,32,147.69,32,94A46.06,46.06,0,0,1,78,48c19.45,0,35.78,10.36,42.6,27a8,8,0,0,0,14.8,0c6.82-16.67,23.15-27,42.6-27a46.06,46.06,0,0,1,46,46C224,147.61,146.24,196.15,128,206.8Z" />
                  )}
                </svg>
              </button>
            )}
            {showPassButton && onPass && (
              <button
                type="button"
                className="btn btn-ghost btn-icon"
                onClick={handlePass}
                aria-label="Pass on this recommendation"
                title="Pass on this recommendation"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 256 256"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M205.66,194.34a8,8,0,0,1-11.32,11.32L128,139.31,61.66,205.66a8,8,0,0,1-11.32-11.32L116.69,128,50.34,61.66A8,8,0,0,1,61.66,50.34L128,116.69l66.34-66.35a8,8,0,0,1,11.32,11.32L139.31,128Z" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
