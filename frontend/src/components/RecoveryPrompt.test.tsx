import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { RecoveryPrompt } from "./RecoveryPrompt";

describe("RecoveryPrompt", () => {
  it("renders the recovery message", () => {
    const onMoodSelect = vi.fn();
    render(<RecoveryPrompt onMoodSelect={onMoodSelect} />);

    expect(
      screen.getByText("Nothing quite matches that. Try one of these instead:")
    ).toBeInTheDocument();
  });

  it("renders all recovery mood chips", () => {
    const onMoodSelect = vi.fn();
    render(<RecoveryPrompt onMoodSelect={onMoodSelect} />);

    const expectedMoods = [
      "feel-good comfort",
      "smart & talky",
      "high-energy thrill",
      "dark & atmospheric",
      "nostalgic 90s/00s vibes",
      "cozy rainy night",
    ];

    expectedMoods.forEach((mood) => {
      expect(screen.getByText(mood)).toBeInTheDocument();
    });
  });

  it("calls onMoodSelect with the mood text when a recovery chip is clicked", async () => {
    const user = userEvent.setup();
    const onMoodSelect = vi.fn();
    render(<RecoveryPrompt onMoodSelect={onMoodSelect} />);

    const chip = screen.getByText("feel-good comfort");
    await user.click(chip);

    expect(onMoodSelect).toHaveBeenCalledWith("feel-good comfort");
    expect(onMoodSelect).toHaveBeenCalledTimes(1);
  });

  it("has proper accessibility labels", () => {
    const onMoodSelect = vi.fn();
    render(<RecoveryPrompt onMoodSelect={onMoodSelect} />);

    const chip = screen.getByLabelText("Try smart & talky instead");
    expect(chip).toBeInTheDocument();
  });

  it("renders chips as buttons", () => {
    const onMoodSelect = vi.fn();
    render(<RecoveryPrompt onMoodSelect={onMoodSelect} />);

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(6);
  });
});
