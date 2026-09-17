import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ShareButton } from "./ShareButton";

describe("ShareButton", () => {
  const originalNavigator = window.navigator;
  const originalLocation = window.location;

  beforeEach(() => {
    delete (window as { location?: unknown }).location;
    (window as { location: unknown }).location = {
      ...originalLocation,
      href: "http://localhost:3000/",
    };
  });

  afterEach(() => {
    Object.defineProperty(window, "navigator", {
      value: originalNavigator,
      writable: true,
    });
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
  });

  it("renders share button with correct aria-label", () => {
    render(<ShareButton query="cozy mystery" />);
    expect(
      screen.getByRole("button", { name: /share results/i }),
    ).toBeInTheDocument();
  });

  it("shows Share text initially", () => {
    render(<ShareButton query="cozy mystery" />);
    expect(screen.getByText("Share")).toBeInTheDocument();
  });

  it("copies URL to clipboard when Web Share API is not available", async () => {
    const user = userEvent.setup();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText: writeTextMock },
      writable: true,
    });

    Object.defineProperty(window.navigator, "share", {
      value: undefined,
      writable: true,
    });

    render(<ShareButton query="cozy mystery" />);

    const button = screen.getByRole("button", { name: /share results/i });
    await user.click(button);

    expect(writeTextMock).toHaveBeenCalledWith(
      "http://localhost:3000/?q=cozy%20mystery",
    );
  });

  it("shows Copied! feedback after copying to clipboard", async () => {
    const user = userEvent.setup();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(window.navigator, "clipboard", {
      value: { writeText: writeTextMock },
      writable: true,
    });

    Object.defineProperty(window.navigator, "share", {
      value: undefined,
      writable: true,
    });

    render(<ShareButton query="cozy mystery" />);

    const button = screen.getByRole("button", { name: /share results/i });
    await user.click(button);

    expect(writeTextMock).toHaveBeenCalledWith(
      "http://localhost:3000/?q=cozy%20mystery",
    );
    
    await screen.findByText("Copied!");
  });

  it("uses Web Share API when available", async () => {
    const shareMock = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(window.navigator, "share", {
      value: shareMock,
      writable: true,
    });

    render(<ShareButton query="epic adventure" />);

    const button = screen.getByRole("button", { name: /share results/i });
    button.click();

    await vi.waitFor(() => {
      expect(shareMock).toHaveBeenCalledWith({
        title: "Moody - Movie Recommendation",
        text: 'Movies for: "epic adventure"',
        url: "http://localhost:3000/?q=epic%20adventure",
      });
    });
  });
});
