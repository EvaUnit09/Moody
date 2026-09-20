import { beforeEach, describe, expect, test, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Movie, MovieRecommendation } from "./api";
import App from "./App";
import { WatchlistProvider } from "./hooks/useWatchlist";

const CACHED_MOVIE: Movie = {
  tmdb_id: 1,
  title: "Cached Movie",
  poster_path: "/poster.jpg",
  year: 2020,
  vote_average: 8.1,
  genres: ["Drama"],
};

const RECOMMENDED_MOVIE: MovieRecommendation = {
  tmdb_id: 2,
  title: "Recommended Movie",
  poster_path: "/recommended.jpg",
  year: 2021,
  vote_average: 7.5,
  genres: ["Action"],
  reason: "High energy and thrilling",
  providers: [],
};

const { getPopularMock, recommendMock } = vi.hoisted(() => ({
  getPopularMock: vi.fn(),
  recommendMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getPopular: getPopularMock,
    recommend: recommendMock,
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
    getPopularMock.mockReturnValue(new Promise(() => {}));

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    expect(screen.getByText("Cached Movie")).toBeInTheDocument();
    expect(document.querySelector(".skeleton-block")).not.toBeInTheDocument();
  });

  test("shows the skeleton while loading when there is no cache", () => {
    readPopularCacheMock.mockReturnValue(null);
    getPopularMock.mockReturnValue(new Promise(() => {}));

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    expect(document.querySelector(".skeleton-block")).toBeInTheDocument();
    expect(screen.queryByText("Cached Movie")).not.toBeInTheDocument();
  });
});

describe("App mood chip and recovery integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    readPopularCacheMock.mockReturnValue([CACHED_MOVIE]);
    getPopularMock.mockResolvedValue([CACHED_MOVIE]);
  });

  test("clicking a mood chip fills the search input and triggers recommendation", async () => {
    const user = userEvent.setup();
    recommendMock.mockResolvedValue([RECOMMENDED_MOVIE]);

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("date night")).toBeInTheDocument();
    });

    const moodChip = screen.getByText("date night");
    await user.click(moodChip);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("date night");
    });

    expect(recommendMock).toHaveBeenCalledWith("date night", expect.any(AbortSignal));
    
    await waitFor(() => {
      expect(screen.getByText("Recommended Movie")).toBeInTheDocument();
    });
  });

  test.skip("shows recovery prompt when search returns empty results", async () => {
    const user = userEvent.setup();
    recommendMock.mockResolvedValue([]);

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    await user.type(screen.getByRole("textbox"), "nonexistent mood");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Nothing quite matches that. Try one of these instead:")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "feel-good comfort" })).toBeInTheDocument();
  });

  test.skip("shows recovery prompt when search returns an error", async () => {
    const user = userEvent.setup();
    recommendMock.mockRejectedValue(new Error("Network error"));

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    await user.type(screen.getByRole("textbox"), "test query");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText(/Nothing quite matches that/)).toBeInTheDocument();
    });

    expect(screen.getByText("cozy rainy night")).toBeInTheDocument();
  });

  test.skip("clicking a recovery chip triggers a new search", async () => {
    const user = userEvent.setup();
    recommendMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([RECOMMENDED_MOVIE]);

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    await user.type(screen.getByRole("textbox"), "bad query");
    await user.click(screen.getByRole("button", { name: "Search" }));

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByText("Thinking...")).not.toBeInTheDocument();
    });

    // Wait for recovery prompt to appear
    await waitFor(() => {
      expect(screen.getByText("feel-good comfort")).toBeInTheDocument();
    });

    const recoveryChip = screen.getByText("feel-good comfort");
    await user.click(recoveryChip);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("feel-good comfort");
    });

    expect(recommendMock).toHaveBeenCalledWith("feel-good comfort", expect.any(AbortSignal));
    
    await waitFor(() => {
      expect(screen.getByText("Recommended Movie")).toBeInTheDocument();
    });
  });
});

describe("More like this functionality", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    readPopularCacheMock.mockReturnValue([CACHED_MOVIE]);
    getPopularMock.mockResolvedValue([CACHED_MOVIE]);
    window.history.replaceState(null, "", "/");
  });

  test("clicking 'More like this' triggers new search with correct query template", async () => {
    const user = userEvent.setup();
    const secondMovie: MovieRecommendation = {
      tmdb_id: 3,
      title: "Another Movie",
      poster_path: "/another.jpg",
      year: 2022,
      vote_average: 8.0,
      genres: ["Thriller"],
      reason: "Suspenseful and gripping",
      providers: [],
    };
    recommendMock
      .mockResolvedValueOnce([RECOMMENDED_MOVIE])
      .mockResolvedValueOnce([secondMovie]);

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    const searchInput = screen.getByRole("textbox");
    await user.clear(searchInput);
    await user.type(searchInput, "dark and moody");
    const searchButton = screen.getByRole("button", { name: "Search" });
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Recommended Movie")).toBeInTheDocument();
    }, { timeout: 3000 });

    const moreLikeThisButton = screen.getByRole("button", { name: "Find more like this" });
    await user.click(moreLikeThisButton);

    await waitFor(() => {
      expect(recommendMock).toHaveBeenCalledWith(
        'movies like Recommended Movie, same vibe as "dark and moody"',
        expect.any(AbortSignal)
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Another Movie")).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByRole("textbox")).toHaveValue('movies like Recommended Movie, same vibe as "dark and moody"');
  });

  test("'More like this' updates URL with new query", async () => {
    const user = userEvent.setup();
    recommendMock.mockResolvedValue([RECOMMENDED_MOVIE]);

    render(
      <WatchlistProvider>
        <App />
      </WatchlistProvider>
    );

    const searchInput = screen.getByRole("textbox");
    await user.clear(searchInput);
    await user.type(searchInput, "test query");
    const searchButton = screen.getByRole("button", { name: "Search" });
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Recommended Movie")).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(window.location.search).toBe("?q=test%20query");

    const moreLikeThisButton = screen.getByRole("button", { name: "Find more like this" });
    await user.click(moreLikeThisButton);

    await waitFor(() => {
      expect(window.location.search).toBe("?q=movies%20like%20Recommended%20Movie%2C%20same%20vibe%20as%20%22test%20query%22");
    });
  });
});
