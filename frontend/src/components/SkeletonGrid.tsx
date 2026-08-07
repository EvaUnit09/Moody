const SKELETON_COUNT = 6;

export function SkeletonGrid() {
  return (
    <div className="results-grid">
      {Array.from({ length: SKELETON_COUNT }, (_, i) => (
        <div key={i} className="card elev-sm movie-card">
          <div className="movie-card-poster skeleton-block" />
          <div className="movie-card-body">
            <div className="skeleton-line skeleton-line-kicker" />
            <div className="skeleton-line skeleton-line-title" />
            <div className="skeleton-line skeleton-line-body" />
          </div>
        </div>
      ))}
    </div>
  );
}
