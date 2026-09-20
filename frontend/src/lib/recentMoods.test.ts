import { describe, it, expect, beforeEach } from "vitest";
import { getRecentMoods, addRecentMood, clearRecentMoods } from "./recentMoods";

describe("recentMoods", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("getRecentMoods", () => {
    it("returns empty array when no recent moods exist", () => {
      expect(getRecentMoods()).toEqual([]);
    });

    it("returns stored recent moods", () => {
      const moods = [
        { query: "slow & melancholic", searchedAt: Date.now() },
        { query: "feel-good comfort", searchedAt: Date.now() - 1000 },
      ];
      localStorage.setItem("moody-recent-moods", JSON.stringify(moods));
      const recent = getRecentMoods();
      expect(recent).toEqual(["slow & melancholic", "feel-good comfort"]);
    });

    it("handles corrupted data gracefully", () => {
      localStorage.setItem("moody-recent-moods", "invalid json");
      expect(getRecentMoods()).toEqual([]);
    });

    it("filters out invalid mood items", () => {
      const moods = [
        { query: "valid mood", searchedAt: Date.now() },
        { query: "", searchedAt: Date.now() },
        { query: 123, searchedAt: Date.now() },
        { searchedAt: Date.now() },
      ];
      localStorage.setItem("moody-recent-moods", JSON.stringify(moods));
      const recent = getRecentMoods();
      expect(recent).toEqual(["valid mood"]);
    });
  });

  describe("addRecentMood", () => {
    it("adds mood to empty list", () => {
      addRecentMood("slow & melancholic");
      const recent = getRecentMoods();
      expect(recent).toHaveLength(1);
      expect(recent[0]).toBe("slow & melancholic");
    });

    it("adds new mood to the beginning", () => {
      addRecentMood("first mood");
      addRecentMood("second mood");
      const recent = getRecentMoods();
      expect(recent[0]).toBe("second mood");
      expect(recent[1]).toBe("first mood");
    });

    it("removes duplicate moods (case-insensitive)", () => {
      addRecentMood("Slow & Melancholic");
      addRecentMood("feel-good comfort");
      addRecentMood("slow & melancholic");
      const recent = getRecentMoods();
      expect(recent).toHaveLength(2);
      expect(recent[0]).toBe("slow & melancholic");
      expect(recent[1]).toBe("feel-good comfort");
    });

    it("limits to maximum of 8 moods", () => {
      for (let i = 1; i <= 10; i++) {
        addRecentMood(`mood ${i}`);
      }
      const recent = getRecentMoods();
      expect(recent).toHaveLength(8);
      expect(recent[0]).toBe("mood 10");
      expect(recent[7]).toBe("mood 3");
    });

    it("trims whitespace from moods", () => {
      addRecentMood("  slow & melancholic  ");
      const recent = getRecentMoods();
      expect(recent[0]).toBe("slow & melancholic");
    });

    it("ignores empty or whitespace-only queries", () => {
      addRecentMood("");
      addRecentMood("   ");
      expect(getRecentMoods()).toEqual([]);
    });

    it("preserves existing valid moods when adding new ones", () => {
      addRecentMood("first mood");
      addRecentMood("second mood");
      addRecentMood("third mood");
      const recent = getRecentMoods();
      expect(recent).toEqual(["third mood", "second mood", "first mood"]);
    });
  });

  describe("clearRecentMoods", () => {
    it("removes all recent moods", () => {
      addRecentMood("mood 1");
      addRecentMood("mood 2");
      clearRecentMoods();
      expect(getRecentMoods()).toEqual([]);
    });

    it("handles clearing when no moods exist", () => {
      clearRecentMoods();
      expect(getRecentMoods()).toEqual([]);
    });
  });

  describe("corrupt schema recovery", () => {
    it("recovers from non-array data", () => {
      localStorage.setItem("moody-recent-moods", JSON.stringify({ broken: "data" }));
      expect(getRecentMoods()).toEqual([]);
    });

    it("filters out items missing query field", () => {
      const moods = [
        { query: "valid mood", searchedAt: Date.now() },
        { searchedAt: Date.now() },
      ];
      localStorage.setItem("moody-recent-moods", JSON.stringify(moods));
      expect(getRecentMoods()).toEqual(["valid mood"]);
    });

    it("filters out items with invalid types", () => {
      const moods = [
        { query: "valid mood", searchedAt: Date.now() },
        { query: 123, searchedAt: "invalid" },
        { query: null, searchedAt: Date.now() },
      ];
      localStorage.setItem("moody-recent-moods", JSON.stringify(moods));
      expect(getRecentMoods()).toEqual(["valid mood"]);
    });

    it("handles localStorage quota exceeded error", () => {
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = () => {
        const error = new Error("QuotaExceededError");
        error.name = "QuotaExceededError";
        throw error;
      };

      addRecentMood("test mood");

      Storage.prototype.setItem = originalSetItem;
    });
  });
});
