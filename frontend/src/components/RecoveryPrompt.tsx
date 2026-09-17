interface RecoveryPromptProps {
  onMoodSelect: (mood: string) => void;
}

const RECOVERY_MOODS = [
  "feel-good comfort",
  "smart & talky",
  "high-energy thrill",
  "dark & atmospheric",
  "nostalgic 90s/00s vibes",
  "cozy rainy night",
];

export function RecoveryPrompt({ onMoodSelect }: RecoveryPromptProps) {
  return (
    <div className="recovery-prompt">
      <p className="recovery-message">
        Nothing quite matches that. Try one of these instead:
      </p>
      <div className="recovery-chips">
        {RECOVERY_MOODS.map((mood) => (
          <button
            key={mood}
            type="button"
            className="tag tag-outline recovery-chip"
            onClick={() => onMoodSelect(mood)}
            aria-label={`Try ${mood} instead`}
          >
            {mood}
          </button>
        ))}
      </div>
    </div>
  );
}
