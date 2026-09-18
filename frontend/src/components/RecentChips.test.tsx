import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { RecentChips } from "./RecentChips";

describe("RecentChips", () => {
  it("renders nothing when recentMoods is empty", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();
    const { container } = render(
      <RecentChips
        recentMoods={[]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders recent mood chips when moods exist", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();
    const moods = ["slow & melancholic", "feel-good comfort", "mind-bending"];

    render(
      <RecentChips
        recentMoods={moods}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    moods.forEach((mood) => {
      expect(screen.getByText(mood)).toBeInTheDocument();
    });
  });

  it("renders Recent label", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["test mood"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText("Recent")).toBeInTheDocument();
  });

  it("renders Clear all button", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["test mood"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    expect(screen.getByText("Clear all")).toBeInTheDocument();
  });

  it("calls onMoodSelect when a chip is clicked", async () => {
    const user = userEvent.setup();
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["slow & melancholic", "feel-good comfort"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    const chip = screen.getByText("slow & melancholic");
    await user.click(chip);

    expect(onMoodSelect).toHaveBeenCalledWith("slow & melancholic");
    expect(onMoodSelect).toHaveBeenCalledTimes(1);
  });

  it("calls onClearAll when Clear all button is clicked", async () => {
    const user = userEvent.setup();
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["test mood"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    const clearButton = screen.getByText("Clear all");
    await user.click(clearButton);

    expect(onClearAll).toHaveBeenCalledTimes(1);
  });

  it("disables all chips when disabled prop is true", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["mood 1", "mood 2"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
        disabled={true}
      />
    );

    const buttons = screen.getAllByRole("button");
    buttons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });

  it("does not disable chips when disabled prop is false", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["mood 1", "mood 2"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
        disabled={false}
      />
    );

    const buttons = screen.getAllByRole("button");
    buttons.forEach((button) => {
      expect(button).not.toBeDisabled();
    });
  });

  it("has proper accessibility labels for mood chips", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["date night"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    const chip = screen.getByLabelText("Search for date night movies");
    expect(chip).toBeInTheDocument();
  });

  it("has proper accessibility label for clear button", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["test mood"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    const clearButton = screen.getByLabelText("Clear recent searches");
    expect(clearButton).toBeInTheDocument();
  });

  it("renders chips with tag-filled class", () => {
    const onMoodSelect = vi.fn();
    const onClearAll = vi.fn();

    render(
      <RecentChips
        recentMoods={["test mood"]}
        onMoodSelect={onMoodSelect}
        onClearAll={onClearAll}
      />
    );

    const chip = screen.getByText("test mood");
    expect(chip).toHaveClass("tag-filled");
    expect(chip).toHaveClass("recent-chip");
  });
});
