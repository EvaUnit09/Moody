import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { MOOD_GROUPS } from "../lib/moodGroups";
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

  it("renders Quiet, Warm, and Wired in order and selects every grouped mood", async () => {
    const user = userEvent.setup();
    const onMoodSelect = vi.fn();
    render(<MoodChips onMoodSelect={onMoodSelect} />);

    expect(screen.getAllByRole("heading").map((heading) => heading.textContent)).toEqual([
      "Quiet",
      "Warm",
      "Wired",
    ]);

    let call = 0;
    for (const group of MOOD_GROUPS) {
      for (const mood of group.moods) {
        call += 1;
        await user.click(screen.getByRole("button", { name: `Search for ${mood} movies` }));
        expect(onMoodSelect).toHaveBeenNthCalledWith(call, mood);
      }
    }
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
