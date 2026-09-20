interface RecentChipsProps {
  recentMoods: string[];
  onMoodSelect: (mood: string) => void;
  onClearAll: () => void;
  disabled?: boolean;
}

export function RecentChips({
  recentMoods,
  onMoodSelect,
  onClearAll,
  disabled = false,
}: RecentChipsProps) {
  if (recentMoods.length === 0) {
    return null;
  }

  return (
    <div className="recent-moods-section">
      <div className="recent-moods-header">
        <span className="text-muted recent-moods-label">Recent</span>
        <button
          type="button"
          className="btn-link text-muted"
          onClick={onClearAll}
          disabled={disabled}
          aria-label="Clear recent searches"
        >
          Clear all
        </button>
      </div>
      <div className="recent-chips">
        {recentMoods.map((mood) => (
          <button
            key={mood}
            type="button"
            className="tag tag-filled recent-chip"
            disabled={disabled}
            onClick={() => onMoodSelect(mood)}
            aria-label={`Search for ${mood} movies`}
          >
            {mood}
          </button>
        ))}
      </div>
    </div>
  );
}
