import { useEffect, useRef } from "react";
import type { Movie } from "../api";
import { MovieCard } from "./MovieCard";

const AUTO_ROTATE_INTERVAL_MS = 4000;
const SCROLL_STEP_RATIO = 0.9;
const EDGE_THRESHOLD_PX = 4;

interface PosterCarouselProps {
  movies: Movie[];
}

export function PosterCarousel({ movies }: PosterCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const isPausedRef = useRef(false);

  function scrollByStep(direction: 1 | -1) {
    const track = trackRef.current;
    if (!track) return;

    const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - EDGE_THRESHOLD_PX;
    const atStart = track.scrollLeft <= EDGE_THRESHOLD_PX;

    if (direction === 1 && atEnd) {
      track.scrollTo({ left: 0, behavior: "smooth" });
      return;
    }
    if (direction === -1 && atStart) {
      track.scrollTo({ left: track.scrollWidth, behavior: "smooth" });
      return;
    }
    track.scrollBy({ left: track.clientWidth * SCROLL_STEP_RATIO * direction, behavior: "smooth" });
  }

  useEffect(() => {
    const timer = setInterval(() => {
      if (!isPausedRef.current) {
        scrollByStep(1);
      }
    }, AUTO_ROTATE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [movies]);

  if (movies.length === 0) {
    return null;
  }

  return (
    <section
      className="carousel"
      onMouseEnter={() => {
        isPausedRef.current = true;
      }}
      onMouseLeave={() => {
        isPausedRef.current = false;
      }}
    >
      <div className="results-heading">
        <h6 className="text-muted">popular right now</h6>
      </div>

      <div className="carousel-viewport">
        <button
          type="button"
          className="btn btn-icon btn-secondary carousel-arrow carousel-arrow-prev"
          aria-label="Scroll left"
          onClick={() => scrollByStep(-1)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>

        <div className="carousel-track" ref={trackRef}>
          {movies.map((movie) => (
            <div key={movie.tmdb_id} className="carousel-item">
              <MovieCard movie={movie} />
            </div>
          ))}
        </div>

        <button
          type="button"
          className="btn btn-icon btn-secondary carousel-arrow carousel-arrow-next"
          aria-label="Scroll right"
          onClick={() => scrollByStep(1)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </div>
    </section>
  );
}
