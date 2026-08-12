import { describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Movie } from "./api";
import App from "./App";

const CACHED_MOVIE: Movie = {
  tmdb_id: 1,
  title: "Cached Movie",
  poster_path: "/poster.jpg",
  year: 2020,
  vote_average: 8.1,
  genres: ["Drama"],
};

const { getPopularMock } = vi.hoisted(() => ({
  getPopularMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getPopular: getPopularMock,
  };
});

const { readPopularCacheMock, writePopularCacheMock } = vi.hoisted(() => ({
  readPopularCacheMock: vi.fn(),
  writePopularCacheMock: vi.fn(),
}));

vi.mock("./lib/popularCache", () => ({
  readPopularCache: readPopularCacheMock,
  writePopularCache: writePopularCacheMock,
}));

describe("App popular carousel loading", () => {
  test("paints the carousel immediately from cache, with no skeleton flash", () => {
    readPopularCacheMock.mockReturnValue([CACHED_MOVIE]);
    getPopularMock.mockReturnValue(new Promise(() => {})); // never resolves in this test

    render(<App />);

    expect(screen.getByText("Cached Movie")).toBeInTheDocument();
    expect(document.querySelector(".skeleton-block")).not.toBeInTheDocument();
  });

  test("shows the skeleton while loading when there is no cache", () => {
    readPopularCacheMock.mockReturnValue(null);
    getPopularMock.mockReturnValue(new Promise(() => {})); // never resolves in this test

    render(<App />);

    expect(document.querySelector(".skeleton-block")).toBeInTheDocument();
    expect(screen.queryByText("Cached Movie")).not.toBeInTheDocument();
  });
});
