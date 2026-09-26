const EXCLUDE_PREFERENCE_KEY = "moody-exclude-passed";

export function getExcludePassedPreference(): boolean {
  try {
    const stored = localStorage.getItem(EXCLUDE_PREFERENCE_KEY);
    if (stored === "false") return false;
    return true;
  } catch {
    return true;
  }
}

export function setExcludePassedPreference(enabled: boolean): void {
  try {
    localStorage.setItem(EXCLUDE_PREFERENCE_KEY, String(enabled));
  } catch (error) {
    console.error("Failed to save exclude preference:", error);
  }
}
