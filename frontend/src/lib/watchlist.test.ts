import { describe, it, expect, beforeEach } from "vitest";
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  isInWatchlist,
  getPassedMovies,
  addToPassedMovies,
  removeFromPassedMovies,
  isMoviePassed,
  exportWatchlist,
  exportWatchlistAsText,
  type WatchlistItem,
} from "./watchlist";
import type { Movie } from "../api";

const mockMovie: Movie = {
  tmdb_id: 123,
  title: "Test Movie",
  poster_path: "/test.jpg",
  year: 2024,
  vote_average: 8.5,
  genres: ["Drama", "Thriller"],
};

describe("watchlist", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("getWatchlist", () => {
    it("returns empty array when no watchlist exists", () => {
      expect(getWatchlist()).toEqual([]);
    });

    it("returns stored watchlist", () => {
      const item: WatchlistItem = { ...mockMovie, addedAt: Date.now() };
      localStorage.setItem("moody-watchlist", JSON.stringify([item]));
      const watchlist = getWatchlist();
      expect(watchlist).toHaveLength(1);
      expect(watchlist[0].tmdb_id).toBe(mockMovie.tmdb_id);
    });

    it("handles corrupted data gracefully", () => {
      localStorage.setItem("moody-watchlist", "invalid json");
      expect(getWatchlist()).toEqual([]);
    });
  });

  describe("addToWatchlist", () => {
    it("adds movie to empty watchlist", () => {
      addToWatchlist(mockMovie);
      const watchlist = getWatchlist();
      expect(watchlist).toHaveLength(1);
      expect(watchlist[0].tmdb_id).toBe(mockMovie.tmdb_id);
      expect(watchlist[0].addedAt).toBeDefined();
    });

    it("does not add duplicate movies", () => {
      addToWatchlist(mockMovie);
      addToWatchlist(mockMovie);
      expect(getWatchlist()).toHaveLength(1);
    });

    it("adds new movies to the beginning", () => {
      const movie2: Movie = { ...mockMovie, tmdb_id: 456, title: "Movie 2" };
      addToWatchlist(mockMovie);
      addToWatchlist(movie2);
      const watchlist = getWatchlist();
      expect(watchlist[0].tmdb_id).toBe(456);
      expect(watchlist[1].tmdb_id).toBe(123);
    });
  });

  describe("removeFromWatchlist", () => {
    it("removes movie from watchlist", () => {
      addToWatchlist(mockMovie);
      removeFromWatchlist(mockMovie.tmdb_id);
      expect(getWatchlist()).toEqual([]);
    });

    it("only removes specified movie", () => {
      const movie2: Movie = { ...mockMovie, tmdb_id: 456, title: "Movie 2" };
      addToWatchlist(mockMovie);
      addToWatchlist(movie2);
      removeFromWatchlist(mockMovie.tmdb_id);
      const watchlist = getWatchlist();
      expect(watchlist).toHaveLength(1);
      expect(watchlist[0].tmdb_id).toBe(456);
    });
  });

  describe("isInWatchlist", () => {
    it("returns false for non-existent movie", () => {
      expect(isInWatchlist(999)).toBe(false);
    });

    it("returns true for movie in watchlist", () => {
      addToWatchlist(mockMovie);
      expect(isInWatchlist(mockMovie.tmdb_id)).toBe(true);
    });
  });

  describe("passed movies", () => {
    describe("getPassedMovies", () => {
      it("returns empty set when no passed movies exist", () => {
        const passed = getPassedMovies();
        expect(passed.size).toBe(0);
      });

      it("returns stored passed movies", () => {
        localStorage.setItem("moody-passed", JSON.stringify([123, 456]));
        const passed = getPassedMovies();
        expect(passed.size).toBe(2);
        expect(passed.has(123)).toBe(true);
        expect(passed.has(456)).toBe(true);
      });

      it("handles corrupted data gracefully", () => {
        localStorage.setItem("moody-passed", "invalid json");
        expect(getPassedMovies().size).toBe(0);
      });
    });

    describe("addToPassedMovies", () => {
      it("adds movie to passed list", () => {
        addToPassedMovies(123);
        expect(isMoviePassed(123)).toBe(true);
      });

      it("handles duplicate additions", () => {
        addToPassedMovies(123);
        addToPassedMovies(123);
        const passed = getPassedMovies();
        expect(passed.size).toBe(1);
      });
    });

    describe("removeFromPassedMovies", () => {
      it("removes movie from passed list", () => {
        addToPassedMovies(123);
        removeFromPassedMovies(123);
        expect(isMoviePassed(123)).toBe(false);
      });
    });

    describe("isMoviePassed", () => {
      it("returns false for non-passed movie", () => {
        expect(isMoviePassed(999)).toBe(false);
      });

      it("returns true for passed movie", () => {
        addToPassedMovies(123);
        expect(isMoviePassed(123)).toBe(true);
      });
    });
  });

  describe("export functions", () => {
    describe("exportWatchlist", () => {
      it("exports empty watchlist as JSON", () => {
        const exported = exportWatchlist();
        expect(JSON.parse(exported)).toEqual([]);
      });

      it("exports watchlist as formatted JSON", () => {
        addToWatchlist(mockMovie);
        const exported = exportWatchlist();
        const parsed = JSON.parse(exported);
        expect(parsed).toHaveLength(1);
        expect(parsed[0].tmdb_id).toBe(mockMovie.tmdb_id);
      });
    });

    describe("exportWatchlistAsText", () => {
      it("exports empty watchlist as empty string", () => {
        expect(exportWatchlistAsText()).toBe("");
      });

      it("exports watchlist as plain text", () => {
        addToWatchlist(mockMovie);
        const exported = exportWatchlistAsText();
        expect(exported).toContain("Test Movie");
        expect(exported).toContain("(2024)");
        expect(exported).toContain("8.5/10");
      });

      it("handles missing data gracefully", () => {
        const movie: Movie = {
          tmdb_id: 789,
          title: "Minimal Movie",
          poster_path: null,
          year: null,
          vote_average: null,
          genres: [],
        };
        addToWatchlist(movie);
        const exported = exportWatchlistAsText();
        expect(exported).toBe("Minimal Movie");
      });
    });
  });
});
