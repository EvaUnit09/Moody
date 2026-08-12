import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Movie } from "../api";
import {
  POPULAR_CACHE_STORAGE_KEY,
  POPULAR_CACHE_STALE_MS,
  readPopularCache,
  writePopularCache,
} from "./popularCache";

const SAMPLE_MOVIES: Movie[] = [
  {
    tmdb_id: 1,
    title: "Sample Movie",
    poster_path: "/poster.jpg",
    year: 2020,
    vote_average: 8.1,
    genres: ["Drama"],
  },
];

describe("popularCache", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns null when nothing has been cached", () => {
    expect(readPopularCache()).toBeNull();
  });

  test("returns the written movies immediately after writing", () => {
    writePopularCache(SAMPLE_MOVIES);
    expect(readPopularCache()).toEqual(SAMPLE_MOVIES);
  });

  test("returns null once the cache entry is older than the staleness window", () => {
    vi.useFakeTimers();
    vi.setSystemTime(0);
    writePopularCache(SAMPLE_MOVIES);

    vi.setSystemTime(POPULAR_CACHE_STALE_MS + 1);
    expect(readPopularCache()).toBeNull();
  });

  test("returns null and does not throw when window.localStorage has malformed JSON", () => {
    window.localStorage.setItem(POPULAR_CACHE_STORAGE_KEY, "not json");
    expect(readPopularCache()).toBeNull();
  });

  test("returns null and does not throw when window.localStorage.getItem throws", () => {
    const spy = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("private browsing");
      });

    expect(readPopularCache()).toBeNull();
    spy.mockRestore();
  });

  test("does not throw when window.localStorage.setItem throws", () => {
    const spy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("quota exceeded");
      });

    expect(() => writePopularCache(SAMPLE_MOVIES)).not.toThrow();
    spy.mockRestore();
  });
});
