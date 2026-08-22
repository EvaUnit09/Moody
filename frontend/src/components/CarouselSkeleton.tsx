const SKELETON_COUNT = 6;

export function CarouselSkeleton() {
  return (
    <section className="carousel">
      <div className="results-heading">
        <h6 className="text-muted">popular right now!</h6>
      </div>

      <div className="carousel-viewport">
        <div className="carousel-track">
          {Array.from({ length: SKELETON_COUNT }, (_, i) => (
            <div key={i} className="carousel-item">
              <div className="card elev-sm movie-card">
                <div className="movie-card-poster skeleton-block" />
                <div className="movie-card-body">
                  <div className="skeleton-line skeleton-line-kicker" />
                  <div className="skeleton-line skeleton-line-title" />
                  <div className="skeleton-line skeleton-line-body" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
