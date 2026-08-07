import type { MovieRecommendation } from "../api";

const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342";

interface MovieCardProps {
  movie: MovieRecommendation;
}

export function MovieCard({ movie }: MovieCardProps) {
  return (
    <div className="movie-card">
      {movie.poster_path ? (
        <img
          src={`${POSTER_BASE_URL}${movie.poster_path}`}
          alt={`${movie.title} poster`}
          loading="lazy"
        />
      ) : (
        <div className="movie-card-poster-placeholder">No poster</div>
      )}
      <h3>{movie.title}</h3>
      <p>{movie.reason}</p>
    </div>
  );
}
