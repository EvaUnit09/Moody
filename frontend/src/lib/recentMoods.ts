const RECENT_MOODS_KEY = "moody-recent-moods";
const MAX_RECENT_MOODS = 8;

interface RecentMood {
  query: string;
  searchedAt: number;
}

function isValidRecentMood(item: unknown): item is RecentMood {
  if (typeof item !== "object" || item === null) return false;
  const obj = item as Record<string, unknown>;
  return (
    typeof obj.query === "string" &&
    obj.query.trim().length > 0 &&
    typeof obj.searchedAt === "number"
  );
}

export function getRecentMoods(): string[] {
  try {
    const stored = localStorage.getItem(RECENT_MOODS_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isValidRecentMood).map((item) => item.query);
  } catch {
    return [];
  }
}

export function addRecentMood(query: string): void {
  const trimmed = query.trim();
  if (!trimmed) return;

  try {
    const stored = localStorage.getItem(RECENT_MOODS_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    const items: RecentMood[] = Array.isArray(parsed)
      ? parsed.filter(isValidRecentMood)
      : [];

    const filtered = items.filter(
      (item) => item.query.toLowerCase() !== trimmed.toLowerCase()
    );

    const newItem: RecentMood = { query: trimmed, searchedAt: Date.now() };
    filtered.unshift(newItem);

    const limited = filtered.slice(0, MAX_RECENT_MOODS);
    localStorage.setItem(RECENT_MOODS_KEY, JSON.stringify(limited));
  } catch (error) {
    if (error instanceof Error && error.name === "QuotaExceededError") {
      console.warn("localStorage quota exceeded. Recent mood not saved.");
    } else {
      console.error("Failed to save recent mood:", error);
    }
  }
}

export function clearRecentMoods(): void {
  try {
    localStorage.removeItem(RECENT_MOODS_KEY);
  } catch (error) {
    console.error("Failed to clear recent moods:", error);
  }
}
