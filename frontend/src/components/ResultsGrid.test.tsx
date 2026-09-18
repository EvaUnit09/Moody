import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultsGrid } from "./ResultsGrid";
import { WatchlistProvider } from "../hooks/useWatchlist";
import { ToastProvider } from "../contexts/ToastContext";
import type { MovieRecommendation } from "../api";
import type { ReactNode } from "react";

function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <WatchlistProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </WatchlistProvider>
  );
}

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
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("returns null when no results", () => {
    const { container } = render(
      <TestWrapper>
        <ResultsGrid results={[]} />
      </TestWrapper>
    );

    expect(container.firstChild).toBeNull();
  });

  it("immediately hides passed movie from grid", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
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
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
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
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1]} />
      </TestWrapper>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();

    const passButton = screen.getByLabelText("Pass on this recommendation");
    await user.click(passButton);

    await waitFor(() => {
      expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    });

    expect(document.querySelector(".results-grid")).not.toBeInTheDocument();
  });

  it("filters already-passed movies on mount", () => {
    localStorage.setItem("moody-passed", JSON.stringify([123, 456]));

    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Test Movie 2")).not.toBeInTheDocument();
    expect(screen.getByText("Test Movie 3")).toBeInTheDocument();
  });

  it("toggles watchlist state correctly", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1]} />
      </TestWrapper>
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

  it("shows undo toast when movie is passed", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </TestWrapper>
    );

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(passButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Hidden")).toBeInTheDocument();
    });

    expect(screen.getByLabelText("Undo")).toBeInTheDocument();
  });

  it("restores passed movie when undo is clicked", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </TestWrapper>
    );

    expect(screen.getByText("Test Movie 1")).toBeInTheDocument();

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(passButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    });

    expect(screen.getByText("Hidden")).toBeInTheDocument();
    const undoButton = screen.getByLabelText("Undo");
    await user.click(undoButton);

    await waitFor(() => {
      expect(screen.getByText("Test Movie 1")).toBeInTheDocument();
    });
  });

  it("shows toast when adding to watchlist", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1]} />
      </TestWrapper>
    );

    const heartButton = screen.getByLabelText("Add to watchlist");
    await user.click(heartButton);

    await waitFor(() => {
      expect(screen.getByText("Added to watchlist")).toBeInTheDocument();
    });
  });

  it("shows toast when removing from watchlist", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1]} />
      </TestWrapper>
    );

    const heartButton = screen.getByLabelText("Add to watchlist");
    await user.click(heartButton);

    await waitFor(() => {
      expect(screen.getByLabelText("Remove from watchlist")).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Remove from watchlist"));

    await waitFor(() => {
      expect(screen.getByText("Removed from watchlist")).toBeInTheDocument();
    });
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
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </TestWrapper>
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
      <TestWrapper>
        <ResultsGrid results={[mockMovie1]} />
      </TestWrapper>
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
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2]} />
      </TestWrapper>
    );

    expect(screen.queryByText("Test Movie 1")).not.toBeInTheDocument();
    expect(screen.getByText("Test Movie 2")).toBeInTheDocument();

    setItemSpy.mockRestore();
  });
});
