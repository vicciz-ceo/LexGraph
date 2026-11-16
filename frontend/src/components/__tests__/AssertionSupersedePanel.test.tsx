// Supersede panel (findings ui:15, pipeline:8): collects the accepted
// assertion that replaces this one, from suggestions or a search, and
// reports the outcome; a refused supersede keeps the form and its reason.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionSupersedePanel } from "../AssertionSupersedePanel";

const suggestions = [{ id: "a-9", proposition: "A newer accepted reading." }];

function open() {
  fireEvent.click(screen.getByRole("button", { name: "Mark as superseded…" }));
}

describe("AssertionSupersedePanel", () => {
  it("starts collapsed and loads nothing", () => {
    const search = vi.fn();
    render(<AssertionSupersedePanel suggestions={suggestions} search={search} onSupersede={vi.fn()} />);

    expect(screen.queryByLabelText("A newer accepted reading.")).not.toBeInTheDocument();
    expect(search).not.toHaveBeenCalled();
  });

  it("supersedes with a suggested assertion", async () => {
    const onSupersede = vi.fn().mockResolvedValue(undefined);
    render(<AssertionSupersedePanel suggestions={suggestions} search={vi.fn()} onSupersede={onSupersede} />);
    open();

    const submit = screen.getByRole("button", { name: "Supersede with selected assertion" });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByLabelText("A newer accepted reading."));
    fireEvent.click(submit);

    await waitFor(() => expect(onSupersede).toHaveBeenCalledWith("a-9"));
    // Done: the form closes.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Mark as superseded…" })).toBeInTheDocument(),
    );
  });

  it("searches only from two characters and lists results once each", async () => {
    const search = vi.fn().mockResolvedValue([
      { id: "a-9", proposition: "A newer accepted reading." },
      { id: "a-7", proposition: "The fee is three months of charges." },
    ]);
    render(<AssertionSupersedePanel suggestions={suggestions} search={search} onSupersede={vi.fn()} />);
    open();

    fireEvent.change(screen.getByLabelText("Search accepted assertions"), { target: { value: "f" } });
    expect(screen.getByText(/Type at least 2 characters/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search accepted assertions"), { target: { value: "fee" } });

    expect(await screen.findByLabelText("The fee is three months of charges.")).toBeInTheDocument();
    expect(search).toHaveBeenCalledTimes(1);
    expect(search).toHaveBeenCalledWith("fee");
    // A suggestion that the search also found is listed once.
    expect(screen.getAllByLabelText("A newer accepted reading.")).toHaveLength(1);
  });

  it("says when the search finds nothing", async () => {
    render(<AssertionSupersedePanel suggestions={[]} search={vi.fn().mockResolvedValue([])} onSupersede={vi.fn()} />);
    open();
    fireEvent.change(screen.getByLabelText("Search accepted assertions"), { target: { value: "zzz" } });

    expect(await screen.findByText("No other accepted assertion matches this search.")).toBeInTheDocument();
  });

  it("drops a choice that a new search no longer lists", async () => {
    const search = vi
      .fn()
      .mockResolvedValueOnce([{ id: "a-7", proposition: "The fee is three months of charges." }])
      .mockResolvedValueOnce([{ id: "a-5", proposition: "Notice must be written." }]);
    render(<AssertionSupersedePanel suggestions={[]} search={search} onSupersede={vi.fn()} />);
    open();
    const box = screen.getByLabelText("Search accepted assertions");
    fireEvent.change(box, { target: { value: "fee" } });
    fireEvent.click(await screen.findByLabelText("The fee is three months of charges."));
    const submit = screen.getByRole("button", { name: "Supersede with selected assertion" });
    expect(submit).toBeEnabled();

    fireEvent.change(box, { target: { value: "notice" } });
    await screen.findByLabelText("Notice must be written.");
    expect(submit).toBeDisabled();
  });

  it("keeps the form and shows the reason when the supersede is refused", async () => {
    const onSupersede = vi.fn().mockRejectedValue(new Error("an assertion cannot supersede itself"));
    render(<AssertionSupersedePanel suggestions={suggestions} search={vi.fn()} onSupersede={onSupersede} />);
    open();
    fireEvent.click(screen.getByLabelText("A newer accepted reading."));
    fireEvent.click(screen.getByRole("button", { name: "Supersede with selected assertion" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("an assertion cannot supersede itself");
    expect(screen.getByLabelText("A newer accepted reading.")).toBeChecked();
  });

  it("reports a failed search", async () => {
    render(
      <AssertionSupersedePanel
        suggestions={[]}
        search={vi.fn().mockRejectedValue(new Error("search unavailable"))}
        onSupersede={vi.fn()}
      />,
    );
    open();
    fireEvent.change(screen.getByLabelText("Search accepted assertions"), { target: { value: "fee" } });

    expect(await screen.findByRole("alert")).toHaveTextContent("search unavailable");
  });

  it("can be cancelled", () => {
    const onSupersede = vi.fn();
    render(<AssertionSupersedePanel suggestions={suggestions} search={vi.fn()} onSupersede={onSupersede} />);
    open();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("button", { name: "Mark as superseded…" })).toBeInTheDocument();
    expect(onSupersede).not.toHaveBeenCalled();
  });
});
