import type { Movie } from "../api";

const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342";

interface MovieCardProps {
  movie: Movie & { reason?: string };
}

export function MovieCard({ movie }: MovieCardProps) {
  return (
    <div className="card elev-sm movie-card">
      {movie.poster_path ? (
        <img
          src={`${POSTER_BASE_URL}${movie.poster_path}`}
          alt={`${movie.title} poster`}
          loading="lazy"
          className="movie-card-poster"
        />
      ) : (
        <div className="movie-card-poster movie-card-poster-placeholder">
          No poster
        </div>
      )}
      <div className="movie-card-body">
        {movie.year && <div className="card-kicker">{movie.year}</div>}
        <div className="card-title">{movie.title}</div>
        {movie.reason && <p className="card-body">{movie.reason}</p>}
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
