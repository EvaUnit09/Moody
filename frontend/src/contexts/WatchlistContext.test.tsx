import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WatchlistProvider, useWatchlist } from "../contexts/WatchlistContext";
import type { Movie } from "../api";

const mockMovie: Movie = {
  tmdb_id: 123,
  title: "Test Movie",
  poster_path: "/test.jpg",
  year: 2024,
  vote_average: 8.5,
  genres: ["Drama"],
};

const mockMovie2: Movie = {
  tmdb_id: 456,
  title: "Another Movie",
  poster_path: "/test2.jpg",
  year: 2023,
  vote_average: 7.8,
  genres: ["Action"],
};

function TestComponent() {
  const { 
    watchlist, 
    passedMovies,
    addMovie, 
    removeMovie, 
    toggleMovie, 
    isInList,
    passMovie,
    unpassMovie,
    isMoviePassed,
  } = useWatchlist();

  return (
    <div>
      <div data-testid="watchlist-count">{watchlist.length}</div>
      <div data-testid="passed-count">{passedMovies.size}</div>
      <div data-testid="is-in-list-123">{isInList(123) ? "yes" : "no"}</div>
      <div data-testid="is-passed-123">{isMoviePassed(123) ? "yes" : "no"}</div>
      <button onClick={() => addMovie(mockMovie)}>Add Movie</button>
      <button onClick={() => removeMovie(123)}>Remove Movie</button>
      <button onClick={() => toggleMovie(mockMovie)}>Toggle Movie</button>
      <button onClick={() => passMovie(123)}>Pass Movie</button>
      <button onClick={() => unpassMovie(123)}>Unpass Movie</button>
      <button onClick={() => addMovie(mockMovie2)}>Add Movie 2</button>
    </div>
  );
}

describe("WatchlistContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("provides watchlist state", () => {
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    expect(screen.getByTestId("watchlist-count")).toHaveTextContent("0");
  });

  it("adds movie to watchlist", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Add Movie"));

    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("1");
      expect(screen.getByTestId("is-in-list-123")).toHaveTextContent("yes");
    });
  });

  it("removes movie from watchlist", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Add Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("1");
    });

    await user.click(screen.getByText("Remove Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("0");
      expect(screen.getByTestId("is-in-list-123")).toHaveTextContent("no");
    });
  });

  it("toggles movie in watchlist", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Toggle Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("1");
    });

    await user.click(screen.getByText("Toggle Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("0");
    });
  });

  it("passes movie immediately", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Pass Movie"));

    await waitFor(() => {
      expect(screen.getByTestId("passed-count")).toHaveTextContent("1");
      expect(screen.getByTestId("is-passed-123")).toHaveTextContent("yes");
    });
  });

  it("unpasses movie", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Pass Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("passed-count")).toHaveTextContent("1");
    });

    await user.click(screen.getByText("Unpass Movie"));
    await waitFor(() => {
      expect(screen.getByTestId("passed-count")).toHaveTextContent("0");
      expect(screen.getByTestId("is-passed-123")).toHaveTextContent("no");
    });
  });

  it("syncs state across multiple components", async () => {
    const user = userEvent.setup();
    
    function Component1() {
      const { addMovie, watchlist } = useWatchlist();
      return (
        <div>
          <button onClick={() => addMovie(mockMovie)}>Add from Component 1</button>
          <div data-testid="component1-count">{watchlist.length}</div>
        </div>
      );
    }

    function Component2() {
      const { watchlist } = useWatchlist();
      return <div data-testid="component2-count">{watchlist.length}</div>;
    }

    render(
      <WatchlistProvider>
        <Component1 />
        <Component2 />
      </WatchlistProvider>
    );

    expect(screen.getByTestId("component1-count")).toHaveTextContent("0");
    expect(screen.getByTestId("component2-count")).toHaveTextContent("0");

    await user.click(screen.getByText("Add from Component 1"));

    await waitFor(() => {
      expect(screen.getByTestId("component1-count")).toHaveTextContent("1");
      expect(screen.getByTestId("component2-count")).toHaveTextContent("1");
    });
  });

  it("maintains order with multiple movies", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <TestComponent />
      </WatchlistProvider>
    );

    await user.click(screen.getByText("Add Movie"));
    await user.click(screen.getByText("Add Movie 2"));

    await waitFor(() => {
      expect(screen.getByTestId("watchlist-count")).toHaveTextContent("2");
    });

    const watchlistData = JSON.parse(localStorage.getItem("moody-watchlist") || "[]");
    expect(watchlistData[0].tmdb_id).toBe(456);
    expect(watchlistData[1].tmdb_id).toBe(123);
  });

  it("throws error when useWatchlist is used outside provider", () => {
    expect(() => {
      render(<TestComponent />);
    }).toThrow("useWatchlist must be used within a WatchlistProvider");
  });
});
