// A render error anywhere used to unmount the whole React tree, leaving an
// empty #root (finding ui:27). The boundary shows a recoverable fallback
// with a way back to the Review Queue.

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "../ErrorBoundary";

const state = { broken: true };

function Fragile() {
  if (state.broken) throw new Error("render failed");
  return <p>Recovered content</p>;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    state.broken = true;
    window.location.hash = "#/assertions/broken";
    // React logs caught render errors; keep the test output readable.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a fallback with a way back to the Review Queue instead of unmounting", () => {
    render(
      <ErrorBoundary>
        <Fragile />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/something went wrong/i);
    expect(screen.getByRole("button", { name: "Back to Review Queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("goes back to the Review Queue and renders its children again", () => {
    render(
      <ErrorBoundary>
        <Fragile />
      </ErrorBoundary>,
    );

    state.broken = false;
    fireEvent.click(screen.getByRole("button", { name: "Back to Review Queue" }));

    expect(window.location.hash).toBe("#/review");
    expect(screen.getByText("Recovered content")).toBeInTheDocument();
  });

  it("clears the error when its reset key changes (e.g. the route changed)", () => {
    const { rerender } = render(
      <ErrorBoundary resetKey="/a">
        <Fragile />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();

    state.broken = false;
    rerender(
      <ErrorBoundary resetKey="/b">
        <Fragile />
      </ErrorBoundary>,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Recovered content")).toBeInTheDocument();
  });
});
