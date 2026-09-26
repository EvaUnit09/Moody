import { describe, it, expect, beforeEach } from "vitest";
import { getExcludePassedPreference, setExcludePassedPreference } from "./excludePreference";

describe("excludePreference", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("getExcludePassedPreference", () => {
    it("returns true by default when no preference is stored", () => {
      expect(getExcludePassedPreference()).toBe(true);
    });

    it("returns stored preference when set to true", () => {
      localStorage.setItem("moody-exclude-passed", "true");
      expect(getExcludePassedPreference()).toBe(true);
    });

    it("returns stored preference when set to false", () => {
      localStorage.setItem("moody-exclude-passed", "false");
      expect(getExcludePassedPreference()).toBe(false);
    });

    it("handles corrupted data gracefully and returns default", () => {
      localStorage.setItem("moody-exclude-passed", "invalid");
      expect(getExcludePassedPreference()).toBe(true);
    });
  });

  describe("setExcludePassedPreference", () => {
    it("stores true preference", () => {
      setExcludePassedPreference(true);
      expect(localStorage.getItem("moody-exclude-passed")).toBe("true");
      expect(getExcludePassedPreference()).toBe(true);
    });

    it("stores false preference", () => {
      setExcludePassedPreference(false);
      expect(localStorage.getItem("moody-exclude-passed")).toBe("false");
      expect(getExcludePassedPreference()).toBe(false);
    });

    it("overwrites previous preference", () => {
      setExcludePassedPreference(true);
      expect(getExcludePassedPreference()).toBe(true);
      
      setExcludePassedPreference(false);
      expect(getExcludePassedPreference()).toBe(false);
    });
  });
});
