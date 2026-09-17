import { useState } from "react";
import type { Movie, WatchProvider } from "../api";

const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342";
const MAX_GENRE_TAGS = 2;

interface MovieCardProps {
  movie: Movie & { reason?: string; providers?: WatchProvider[] };
}

export function MovieCard({ movie }: MovieCardProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const posterClassName = `movie-card-poster${isLoaded ? " movie-card-poster-loaded" : ""}`;
  const providers = movie.providers || [];

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
      </div>
    </div>
  );
}
