interface MoodChipsProps {
  onMoodSelect: (mood: string) => void;
  disabled?: boolean;
}

const STARTER_MOODS = [
  "slow & melancholic",
  "date night",
  "nothing heavy",
  "feel-good comfort",
  "mind-bending",
  "cozy rainy night",
  "high-energy thrill",
  "smart & talky",
  "nostalgic 90s/00s vibes",
  "dark & atmospheric",
];

export function MoodChips({ onMoodSelect, disabled = false }: MoodChipsProps) {
  return (
    <div className="mood-chips">
      {STARTER_MOODS.map((mood) => (
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
  );
}
