import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SortPills } from "./SortPills";

describe("SortPills", () => {
  it("renders all sort options", () => {
    const handleChange = vi.fn();
    render(<SortPills selectedSort="best-match" onSortChange={handleChange} />);

    expect(screen.getByText("Best match")).toBeInTheDocument();
    expect(screen.getByText("Highest rated")).toBeInTheDocument();
    expect(screen.getByText("Newest")).toBeInTheDocument();
    expect(screen.getByText("Title A–Z")).toBeInTheDocument();
  });

  it("marks selected sort as active", () => {
    const handleChange = vi.fn();
    render(<SortPills selectedSort="highest-rated" onSortChange={handleChange} />);

    const highestRatedButton = screen.getByText("Highest rated");
    expect(highestRatedButton).toHaveAttribute("aria-checked", "true");
    expect(highestRatedButton).toHaveClass("sort-pill-active");

    const bestMatchButton = screen.getByText("Best match");
    expect(bestMatchButton).toHaveAttribute("aria-checked", "false");
    expect(bestMatchButton).not.toHaveClass("sort-pill-active");
  });

  it("calls onSortChange when a pill is clicked", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<SortPills selectedSort="best-match" onSortChange={handleChange} />);

    await user.click(screen.getByText("Highest rated"));
    expect(handleChange).toHaveBeenCalledWith("highest-rated");
  });

  it("has proper radiogroup semantics", () => {
    const handleChange = vi.fn();
    const { container } = render(<SortPills selectedSort="best-match" onSortChange={handleChange} />);

    const radiogroup = container.querySelector('[role="radiogroup"]');
    expect(radiogroup).toBeInTheDocument();
    expect(radiogroup).toHaveAttribute("aria-label", "Sort results");

    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(4);
  });

  it("updates active state when selection changes", () => {
    const handleChange = vi.fn();
    const { rerender } = render(<SortPills selectedSort="best-match" onSortChange={handleChange} />);

    expect(screen.getByText("Best match")).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("Newest")).toHaveAttribute("aria-checked", "false");

    rerender(<SortPills selectedSort="newest" onSortChange={handleChange} />);

    expect(screen.getByText("Best match")).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("Newest")).toHaveAttribute("aria-checked", "true");
  });
});
