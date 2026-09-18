import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultsGrid } from "./ResultsGrid";
import { WatchlistProvider } from "../hooks/useWatchlist";
import type { MovieRecommendation } from "../api";

const mockMovie1: MovieRecommendation = {
  tmdb_id: 123,
  title: "Test Movie 1",
  poster_path: "/test1.jpg",
  year: 2024,
  vote_average: 8.5,
  genres: ["Drama"],
  reason: "Great drama",
  providers: [],
};

const mockMovie2: MovieRecommendation = {
  tmdb_id: 456,
  title: "Test Movie 2",
  poster_path: "/test2.jpg",
  year: 2023,
  vote_average: 7.8,
  genres: ["Action"],
  reason: "Exciting action",
  providers: [],
};

const mockMovie3: MovieRecommendation = {
  tmdb_id: 789,
  title: "Test Movie 3",
  poster_path: "/test3.jpg",
  year: 2022,
  vote_average: 9.0,
  genres: ["Comedy"],
  reason: "Hilarious comedy",
  providers: [],
};

describe("ResultsGrid", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders all movies initially", () => {
    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </WatchlistProvider>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("returns null when no results", () => {
    const { container } = render(
      <WatchlistProvider>
        <ResultsGrid results={[]} />
      </WatchlistProvider>
    );

    expect(container.firstChild).toBeNull();
  });

  it("immediately hides passed movie from grid", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </WatchlistProvider>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(passButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    });

    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("hides multiple passed movies", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </WatchlistProvider>
    );

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    
    await user.click(passButtons[0]);
    await waitFor(() => {
      expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    });

    const remainingPassButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(remainingPassButtons[0]);
    await waitFor(() => {
      expect(screen.queryByText("Test Movie 2")).not.toBeInTheDocument();
    });

    expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Test Movie 2")).not.toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("returns null when all movies are passed", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1]} />
      </WatchlistProvider>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();

    const passButton = screen.getByLabelText("Pass on this recommendation");
    await user.click(passButton);

    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it("filters already-passed movies on mount", () => {
    localStorage.setItem("moody-passed", JSON.stringify([123, 456]));

    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </WatchlistProvider>
    );

    expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Test Movie 2")).not.toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("toggles watchlist state correctly", async () => {
    const user = userEvent.setup();
    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1]} />
      </WatchlistProvider>
    );

    const heartButton = screen.getByLabelText("Add to watchlist");
    await user.click(heartButton);

    await waitFor(() => {
      expect(screen.getByLabelText("Remove from watchlist")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Remove from watchlist"));

    await waitFor(() => {
      expect(screen.getByLabelText("Add to watchlist")).toBeInTheDocument();
    });
  });

  it("calls onMoreLikeThis with title and current query when button clicked", async () => {
    const user = userEvent.setup();
    const onMoreLikeThis = vi.fn();
    render(
      <WatchlistProvider>
        <ResultsGrid 
          results={[mockMovie1, mockMovie2]} 
          currentQuery="dark and moody films"
          onMoreLikeThis={onMoreLikeThis}
        />
      </WatchlistProvider>
    );

    const moreLikeThisButtons = screen.getAllByRole("button", { name: "Find more like this" });
    await user.click(moreLikeThisButtons[0]);

    expect(onMoreLikeThis).toHaveBeenCalledTimes(1);
    expect(onMoreLikeThis).toHaveBeenCalledWith("Test Movie 1", "dark and moody films");
  });

  it("renders 'More like this' button when onMoreLikeThis provided", () => {
    const onMoreLikeThis = vi.fn();
    render(
      <WatchlistProvider>
        <ResultsGrid 
          results={[mockMovie1]} 
          currentQuery="test query"
          onMoreLikeThis={onMoreLikeThis}
        />
      </WatchlistProvider>
    );

    expect(screen.getByRole("button", { name: "Find more like this" })).toBeInTheDocument();
  });

  it("does not render 'More like this' button when onMoreLikeThis not provided", () => {
    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1]} />
      </WatchlistProvider>
    );

    expect(screen.queryByRole("button", { name: "Find more like this" })).not.toBeInTheDocument();
  });

  it("does not render 'More like this' button when currentQuery is empty", () => {
    const onMoreLikeThis = vi.fn();
    render(
      <WatchlistProvider>
        <ResultsGrid 
          results={[mockMovie1]} 
          currentQuery=""
          onMoreLikeThis={onMoreLikeThis}
        />
      </WatchlistProvider>
    );

    expect(screen.queryByRole("button", { name: "Find more like this" })).not.toBeInTheDocument();
  });
});

describe("ResultsGrid QuotaExceeded handling", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("gracefully handles QuotaExceededError when passing movie", async () => {
    const user = userEvent.setup();
    const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      const error = new Error("QuotaExceededError");
      error.name = "QuotaExceededError";
      throw error;
    });

    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </WatchlistProvider>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(passButtons[0]);

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      "localStorage quota exceeded. Watchlist changes not saved."
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();

    setItemSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  it("gracefully handles QuotaExceededError when adding to watchlist", async () => {
    const user = userEvent.setup();
    const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      const error = new Error("QuotaExceededError");
      error.name = "QuotaExceededError";
      throw error;
    });

    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1]} />
      </WatchlistProvider>
    );

    const heartButton = screen.getByLabelText("Add to watchlist");
    await user.click(heartButton);

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      "localStorage quota exceeded. Watchlist changes not saved."
    );

    expect(screen.getByLabelText("Add to watchlist")).toBeInTheDocument();

    setItemSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  it("continues working after QuotaExceeded for reads", async () => {
    localStorage.setItem("moody-passed", JSON.stringify([123]));
    
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      const error = new Error("QuotaExceededError");
      error.name = "QuotaExceededError";
      throw error;
    });

    render(
      <WatchlistProvider>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </WatchlistProvider>
    );

    expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();

    setItemSpy.mockRestore();
  });
});
