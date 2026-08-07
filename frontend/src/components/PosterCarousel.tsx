import { useEffect, useRef, useState } from "react";
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
  const isHoveredRef = useRef(false);
  const cooldownUntilRef = useRef(0);
  const [progress, setProgress] = useState(0);

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

  function handleManualNav(direction: 1 | -1) {
    cooldownUntilRef.current = Date.now() + AUTO_ROTATE_INTERVAL_MS;
    scrollByStep(direction);
  }

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) return;

    const timer = setInterval(() => {
      if (!isHoveredRef.current && Date.now() >= cooldownUntilRef.current) {
        scrollByStep(1);
      }
    }, AUTO_ROTATE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [movies]);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    function updateProgress() {
      if (!track) return;
      const max = track.scrollWidth - track.clientWidth;
      setProgress(max > 0 ? track.scrollLeft / max : 0);
    }

    updateProgress();
    track.addEventListener("scroll", updateProgress, { passive: true });
    return () => track.removeEventListener("scroll", updateProgress);
  }, [movies]);

  if (movies.length === 0) {
    return null;
  }

  return (
    <section
      className="carousel"
      onMouseEnter={() => {
        isHoveredRef.current = true;
      }}
      onMouseLeave={() => {
        isHoveredRef.current = false;
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
          onClick={() => handleManualNav(-1)}
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
          onClick={() => handleManualNav(1)}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      </div>

      <div className="carousel-progress-track">
        <div
          className="carousel-progress-bar"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </section>
  );
}
