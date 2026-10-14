import { MOOD_GROUPS } from "../lib/moodGroups";

interface MoodChipsProps {
  onMoodSelect: (mood: string) => void;
  disabled?: boolean;
}

export function MoodChips({ onMoodSelect, disabled = false }: MoodChipsProps) {
  return (
    <div className="mood-groups">
      {MOOD_GROUPS.map((group) => (
        <section key={group.id} className="mood-group">
          <h6 className="text-muted recent-moods-label">{group.label}</h6>
          <div className="mood-chips">
            {group.moods.map((mood) => (
              <button
                key={mood}
                type="button"
                className="tag tag-outline mood-chip"
                disabled={disabled}
                onClick={() => onMoodSelect(mood)}
                aria-label={`Search for ${mood} movies`}
              >
                {mood}
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
