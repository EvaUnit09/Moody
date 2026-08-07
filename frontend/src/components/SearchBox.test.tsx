import { describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchBox } from "./SearchBox";

const EXAMPLE_LABELS = [
  "something slow and melancholic",
  "a movie that feels like a rainy sunday",
  "high energy, no thinking required",
  "a heist that goes almost too smoothly",
];

describe("SearchBox", () => {
  test("renders the mood tag, input, and a disabled Search button", () => {
    render(<SearchBox onSearch={() => {}} isLoading={false} />);

    expect(screen.getByText("mood, not genre")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
  });

  test("enables the Search button once text is typed, and submits the trimmed query", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBox onSearch={onSearch} isLoading={false} />);

    await user.type(screen.getByRole("textbox"), "  cozy rainy day  ");
    const button = screen.getByRole("button", { name: "Search" });
    expect(button).toBeEnabled();

    await user.click(button);
    expect(onSearch).toHaveBeenCalledWith("cozy rainy day");
  });

  test("does not call onSearch for a whitespace-only query", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBox onSearch={onSearch} isLoading={false} />);

    await user.type(screen.getByRole("textbox"), "   ");
    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
    expect(onSearch).not.toHaveBeenCalled();
  });

  test("renders one example chip per placeholder when the input is empty", () => {
    render(<SearchBox onSearch={() => {}} isLoading={false} />);

    for (const label of EXAMPLE_LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  test("clicking a chip searches with its exact label and hides the chips", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBox onSearch={onSearch} isLoading={false} />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_LABELS[0] }));

    expect(onSearch).toHaveBeenCalledWith(EXAMPLE_LABELS[0]);
    expect(screen.getByRole("textbox")).toHaveValue(EXAMPLE_LABELS[0]);
    expect(
      screen.queryByRole("button", { name: EXAMPLE_LABELS[1] }),
    ).not.toBeInTheDocument();
  });

  test("disables the input, Search button, and chips while loading", () => {
    render(<SearchBox onSearch={() => {}} isLoading={true} />);

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Thinking..." })).toBeDisabled();
    for (const label of EXAMPLE_LABELS) {
      expect(screen.getByRole("button", { name: label })).toBeDisabled();
    }
  });
});
