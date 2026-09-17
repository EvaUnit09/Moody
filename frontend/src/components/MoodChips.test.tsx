import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { MoodChips } from "./MoodChips";

describe("MoodChips", () => {
  it("renders all mood chip buttons", () => {
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} />);

    const expectedMoods = [
      "slow & melancholic",
      "date night",
      "nothing heavy",
      "feel-good comfort",
      "mind-bending",
      "cozy rainy night",
      "high-energy thrill",
      "smart & talky",
      "nostalgic 90s/00s vibes",
      "dark & atmospheric",
    ];

    expectedMoods.forEach((mood) => {
      expect(screen.getByText(mood)).toBeInTheDocument();
    });
  });

  it("calls onMoodSelect with the mood text when a chip is clicked", async () => {
    const user = userEvent.setup();
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} />);

    const chip = screen.getByText("date night");
    await user.click(chip);

    expect(onMoodSelect).toHaveBeenCalledWith("date night");
    expect(onMoodSelect).toHaveBeenCalledTimes(1);
  });

  it("disables all chips when disabled prop is true", () => {
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} disabled={true} />);

    const chips = screen.getAllByRole("button");
    chips.forEach((chip) => {
      expect(chip).toBeDisabled();
    });
  });

  it("does not disable chips when disabled prop is false", () => {
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} disabled={false} />);

    const chips = screen.getAllByRole("button");
    chips.forEach((chip) => {
      expect(chip).not.toBeDisabled();
    });
  });

  it("has proper accessibility labels", () => {
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} />);

    const chip = screen.getByLabelText("Search for date night movies");
    expect(chip).toBeInTheDocument();
  });
});
