import { describe, it, expect } from "vitest";
import { MOOD_GROUPS } from "./moodGroups";

describe("MOOD_GROUPS", () => {
  it("uses the labels Quiet, Warm, and Wired", () => {
    expect(MOOD_GROUPS.map((group) => ({ id: group.id, label: group.label }))).toEqual([
      { id: "quiet", label: "Quiet" },
      { id: "warm", label: "Warm" },
      { id: "wired", label: "Wired" },
    ]);
  });

  it("keeps the mood order inside each group", () => {
    expect(MOOD_GROUPS.map((group) => group.moods)).toEqual([
      ["slow & melancholic", "cozy rainy night", "dark & atmospheric"],
      [
        "feel-good comfort",
        "nothing heavy",
        "date night",
        "nostalgic 90s/00s vibes",
      ],
      ["high-energy thrill", "mind-bending", "smart & talky"],
    ]);
  });

  it("lists ten unique mood strings", () => {
    const moods = MOOD_GROUPS.flatMap((group) => group.moods);
    expect(moods).toHaveLength(10);
    expect(new Set(moods).size).toBe(10);
  });
});
