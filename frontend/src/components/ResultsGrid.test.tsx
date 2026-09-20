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

const mockMovie4: MovieRecommendation = {
  tmdb_id: 101,
  title: "Alpha Movie",
  poster_path: "/alpha.jpg",
  year: 2021,
  vote_average: 7.0,
  genres: ["Sci-Fi"],
  reason: "Mind-bending sci-fi",
  providers: [],
};

const mockMovie5: MovieRecommendation = {
  tmdb_id: 202,
  title: "Zebra Movie",
  poster_path: "/zebra.jpg",
  year: 2025,
  vote_average: 6.5,
  genres: ["Documentary"],
  reason: "Fascinating documentary",
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

  it("renders sort pills", () => {
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    expect(screen.getByText("Best match")).toBeInTheDocument();
    expect(screen.getByText("Highest rated")).toBeInTheDocument();
    expect(screen.getByText("Newest")).toBeInTheDocument();
    expect(screen.getByText("Title A–Z")).toBeInTheDocument();
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

describe("ResultsGrid Sorting", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("sorts by highest rated", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Highest rated"));

    const movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 3 poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "Test Movie 2 poster");
  });

  it("sorts by newest year", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3, mockMovie5]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Newest"));

    const movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Zebra Movie poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "Test Movie 2 poster");
    expect(movieCards[3]).toHaveAttribute("alt", "Test Movie 3 poster");
  });

  it("sorts by title A-Z", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie4, mockMovie5]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Title A–Z"));

    const movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Alpha Movie poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "Zebra Movie poster");
  });

  it("restores original API order when selecting best match", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Highest rated"));
    let movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 3 poster");

    await user.click(screen.getByText("Best match"));
    movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 2 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "Test Movie 3 poster");
  });

  it("handles movies with null ratings", async () => {
    const movieWithNullRating: MovieRecommendation = {
      ...mockMovie1,
      tmdb_id: 999,
      title: "No Rating Movie",
      vote_average: null,
    };

    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, movieWithNullRating, mockMovie3]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Highest rated"));

    const movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 3 poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "No Rating Movie poster");
  });

  it("handles movies with null years", async () => {
    const movieWithNullYear: MovieRecommendation = {
      ...mockMovie1,
      tmdb_id: 998,
      title: "No Year Movie",
      year: null,
    };

    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, movieWithNullYear, mockMovie3]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Newest"));

    const movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 3 poster");
    expect(movieCards[2]).toHaveAttribute("alt", "No Year Movie poster");
  });

  it("maintains sort when passing movies", async () => {
    const user = userEvent.setup();
    render(
      <TestWrapper>
        <ResultsGrid results={[mockMovie1, mockMovie2, mockMovie3]} />
      </TestWrapper>
    );

    await user.click(screen.getByText("Highest rated"));

    let movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 3 poster");

    const passButtons = screen.getAllByLabelText("Pass on this recommendation");
    await user.click(passButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText("Test Movie 3")).not.toBeInTheDocument();
    });

    movieCards = screen.getAllByRole("img");
    expect(movieCards[0]).toHaveAttribute("alt", "Test Movie 1 poster");
    expect(movieCards[1]).toHaveAttribute("alt", "Test Movie 2 poster");
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
    expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
    expect(screen.getByText("Couldn't save — storage full")).toBeInTheDocument();

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
    expect(screen.queryByText("Added to watchlist")).not.toBeInTheDocument();
    expect(screen.getByText("Couldn't save — storage full")).toBeInTheDocument();

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
