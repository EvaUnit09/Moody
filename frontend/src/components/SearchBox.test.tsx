import { describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchBox } from "./SearchBox";

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

  test("disables the input and Search button while loading", () => {
    render(<SearchBox onSearch={() => {}} isLoading={true} />);

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Thinking..." })).toBeDisabled();
  });

  test("works as a controlled component when value and onChange are provided", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    const onChange = vi.fn();
    
    const { rerender } = render(
      <SearchBox 
        onSearch={onSearch} 
        isLoading={false}
        value="initial query"
        onChange={onChange}
      />
    );

    expect(screen.getByRole("textbox")).toHaveValue("initial query");

    await user.type(screen.getByRole("textbox"), "x");
    expect(onChange).toHaveBeenCalledWith("initial queryx");
    expect(onChange).toHaveBeenCalledTimes(1);

    rerender(
      <SearchBox 
        onSearch={onSearch} 
        isLoading={false}
        value="updated query"
        onChange={onChange}
      />
    );

    expect(screen.getByRole("textbox")).toHaveValue("updated query");
  });

  test("works as an uncontrolled component when value and onChange are not provided", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    
    render(<SearchBox onSearch={onSearch} isLoading={false} />);

    const input = screen.getByRole("textbox");
    expect(input).toHaveValue("");

    await user.type(input, "test query");
    expect(input).toHaveValue("test query");

    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(onSearch).toHaveBeenCalledWith("test query");
  });

  test("accepts external value prop to control the input", () => {
    const { rerender } = render(<SearchBox onSearch={() => {}} isLoading={false} value="" />);
    expect(screen.getByRole("textbox")).toHaveValue("");

    rerender(<SearchBox onSearch={() => {}} isLoading={false} value="external value" />);
    expect(screen.getByRole("textbox")).toHaveValue("external value");
  });

  test("shows exclude toggle when hasPassedMovies is true", () => {
    render(
      <SearchBox 
        onSearch={() => {}} 
        isLoading={false}
        hasPassedMovies={true}
        excludePassedMovies={true}
        onToggleExcludePassed={() => {}}
      />
    );

    expect(screen.getByLabelText(/don.t show hidden/i)).toBeInTheDocument();
  });

  test("does not show exclude toggle when hasPassedMovies is false", () => {
    render(
      <SearchBox 
        onSearch={() => {}} 
        isLoading={false}
        hasPassedMovies={false}
        excludePassedMovies={true}
        onToggleExcludePassed={() => {}}
      />
    );

    expect(screen.queryByLabelText(/don.t show hidden/i)).not.toBeInTheDocument();
  });

  test("calls onToggleExcludePassed when checkbox is clicked", async () => {
    const user = userEvent.setup();
    const onToggleExcludePassed = vi.fn();
    
    render(
      <SearchBox 
        onSearch={() => {}} 
        isLoading={false}
        hasPassedMovies={true}
        excludePassedMovies={true}
        onToggleExcludePassed={onToggleExcludePassed}
      />
    );

    const checkbox = screen.getByLabelText(/don.t show hidden/i);
    expect(checkbox).toBeChecked();

    await user.click(checkbox);
    expect(onToggleExcludePassed).toHaveBeenCalledWith(false);
  });

  test("toggle reflects excludePassedMovies prop state", () => {
    const { rerender } = render(
      <SearchBox 
        onSearch={() => {}} 
        isLoading={false}
        hasPassedMovies={true}
        excludePassedMovies={true}
        onToggleExcludePassed={() => {}}
      />
    );

    expect(screen.getByLabelText(/don.t show hidden/i)).toBeChecked();

    rerender(
      <SearchBox 
        onSearch={() => {}} 
        isLoading={false}
        hasPassedMovies={true}
        excludePassedMovies={false}
        onToggleExcludePassed={() => {}}
      />
    );

    expect(screen.getByLabelText(/don.t show hidden/i)).not.toBeChecked();
  });
});
