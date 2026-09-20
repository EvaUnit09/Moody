import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastProvider, useToast } from "./ToastContext";

function TestComponent() {
  const { showToast } = useToast();

  return (
    <div>
      <button onClick={() => showToast("Test message", { duration: 1000 })}>
        Show Toast
      </button>
      <button onClick={() => showToast("With action", {
        action: { label: "Action", onClick: () => {} },
        duration: 5000,
      })}>
        Show Toast with Action
      </button>
    </div>
  );
}

describe("ToastContext", () => {

  it("throws error when useToast is called outside ToastProvider", () => {
    expect(() => {
      render(<TestComponent />);
    }).toThrow("useToast must be used within a ToastProvider");
  });

  it("shows toast message when triggered", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast"));

    expect(screen.getByText("Test message")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows toast with action button", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast with Action"));

    expect(screen.getByText("With action")).toBeInTheDocument();
    expect(screen.getByLabelText("Action")).toBeInTheDocument();
  });

  it("auto-dismisses toast after duration", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast"));
    expect(screen.getByText("Test message")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText("Test message")).not.toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("dismisses toast when close button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast"));
    expect(screen.getByText("Test message")).toBeInTheDocument();

    const closeButton = screen.getByLabelText("Dismiss notification");
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("Test message")).not.toBeInTheDocument();
    });
  });

  it("dismisses toast when action button is clicked", async () => {
    const actionMock = vi.fn();
    const user = userEvent.setup();

    function TestActionComponent() {
      const { showToast } = useToast();

      return (
        <button onClick={() => showToast("Action toast", {
          action: { label: "Do it", onClick: actionMock },
          duration: 5000,
        })}>
          Show
        </button>
      );
    }

    render(
      <ToastProvider>
        <TestActionComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show"));
    expect(screen.getByText("Action toast")).toBeInTheDocument();

    const actionButton = screen.getByLabelText("Do it");
    await user.click(actionButton);

    expect(actionMock).toHaveBeenCalledOnce();

    await waitFor(() => {
      expect(screen.queryByText("Action toast")).not.toBeInTheDocument();
    });
  });

  it("supports multiple toasts at once", async () => {
    const user = userEvent.setup();

    function MultiToastComponent() {
      const { showToast } = useToast();

      return (
        <div>
          <button onClick={() => showToast("First", { duration: 5000 })}>
            First
          </button>
          <button onClick={() => showToast("Second", { duration: 5000 })}>
            Second
          </button>
        </div>
      );
    }

    render(
      <ToastProvider>
        <MultiToastComponent />
      </ToastProvider>
    );

    await user.click(screen.getByRole("button", { name: "First" }));
    await user.click(screen.getByRole("button", { name: "Second" }));

    expect(screen.getAllByText("First")).toHaveLength(2);
    expect(screen.getAllByText("Second")).toHaveLength(2);

    const toasts = screen.getAllByRole("status");
    expect(toasts).toHaveLength(2);
  });

  it("Escape dismisses only the most recently shown toast, not all of them", async () => {
    const user = userEvent.setup();

    function MultiToastComponent() {
      const { showToast } = useToast();

      return (
        <div>
          <button onClick={() => showToast("First", { duration: 5000 })}>
            First
          </button>
          <button onClick={() => showToast("Second", { duration: 5000 })}>
            Second
          </button>
        </div>
      );
    }

    render(
      <ToastProvider>
        <MultiToastComponent />
      </ToastProvider>
    );

    await user.click(screen.getByRole("button", { name: "First" }));
    await user.click(screen.getByRole("button", { name: "Second" }));

    expect(screen.getAllByRole("status")).toHaveLength(2);

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.getAllByRole("status")).toHaveLength(1);
    });
    expect(screen.getByRole("status")).toHaveTextContent("First");
  });

  it("cancels pending timers on unmount without warnings", async () => {
    const user = userEvent.setup();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const { unmount } = render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast"));
    expect(screen.getByText("Test message")).toBeInTheDocument();

    unmount();

    await new Promise((resolve) => setTimeout(resolve, 1200));

    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
    cleanup();
  });

  it("has accessible ARIA attributes", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await user.click(screen.getByText("Show Toast"));

    const container = screen.getByRole("region");
    expect(container).toHaveAttribute("aria-live", "polite");
    expect(container).toHaveAttribute("aria-label", "Notifications");

    const toast = screen.getByRole("status");
    expect(toast).toBeInTheDocument();
  });
});
