// SourcePicker — pager (ui:29), labels for pre-selected values, and the
// empty-state copy. The API client is mocked; no network.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../api/client";
import { SourcePicker } from "../SourcePicker";

vi.mock("../../api/client", () => ({ api: { sources: vi.fn() } }));

function page(count: number, total: number, prefix = "doc") {
  return {
    items: Array.from({ length: count }, (_, i) => ({ id: `${prefix}-${i}`, type: "Document", label: `${prefix} ${i}` })),
    total,
  };
}

beforeEach(() => {
  vi.mocked(api.sources).mockReset();
});

describe("SourcePicker", () => {
  it("hides the pager when every source fits on one page", async () => {
    vi.mocked(api.sources).mockResolvedValue(page(3, 3));
    render(<SourcePicker matterId="m1" kind="entities" label="Subject source" value="" onSelect={vi.fn()} />);
    await screen.findByRole("option", { name: "doc 2" });
    expect(screen.queryByRole("button", { name: "More sources" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Previous sources" })).not.toBeInTheDocument();
  });

  it("pages with styled buttons and says which sources are shown", async () => {
    vi.mocked(api.sources).mockImplementation(async (_m, _k, _q = "", offset = 0) =>
      offset === 0 ? page(50, 120) : page(50, 120, "next"),
    );
    const user = userEvent.setup();
    render(<SourcePicker matterId="m1" kind="entities" label="Subject source" value="" onSelect={vi.fn()} />);
    await screen.findByRole("option", { name: "doc 49" });
    const more = screen.getByRole("button", { name: "More sources" });
    const previous = screen.getByRole("button", { name: "Previous sources" });
    expect(more).toHaveClass("btn", "btn--secondary", "btn--sm");
    expect(previous).toHaveClass("btn", "btn--secondary", "btn--sm");
    expect(previous).toBeDisabled();
    expect(screen.getByText("Showing 1–50 of 120")).toBeInTheDocument();
    await user.click(more);
    await screen.findByRole("option", { name: "next 0" });
    expect(api.sources).toHaveBeenLastCalledWith("m1", "entities", "", 50);
    expect(screen.getByText("Showing 51–100 of 120")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Previous sources" })).toBeEnabled());
  });

  it("labels a pre-selected value that is not among the loaded options", async () => {
    vi.mocked(api.sources).mockResolvedValue(page(2, 2));
    render(
      <SourcePicker matterId="m1" kind="entities" label="Subject source" value="def-1"
        valueLabel="Definition from the link you followed" onSelect={vi.fn()} />,
    );
    await screen.findByRole("option", { name: "doc 1" });
    expect(screen.getByLabelText("Subject source")).toHaveValue("def-1");
    expect(screen.getByRole("option", { name: "Definition from the link you followed" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "def-1" })).not.toBeInTheDocument();
  });

  it("tells an empty matter apart from a search without results", async () => {
    vi.mocked(api.sources).mockResolvedValue({ items: [], total: 0 });
    const user = userEvent.setup();
    render(<SourcePicker matterId="m1" kind="source-spans" label="Evidence source" value="" onSelect={vi.fn()} />);
    expect(await screen.findByText("This matter has no source passages yet.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Search evidence source"), "notice");
    expect(await screen.findByText("No sources match “notice”. Change your search.")).toBeInTheDocument();
  });

  it("reports the selected source with its type", async () => {
    vi.mocked(api.sources).mockResolvedValue({ items: [{ id: "art-1", type: "Article", label: "MSA / 8 Notices" }], total: 1 });
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<SourcePicker matterId="m1" kind="entities" label="Subject source" value="" onSelect={onSelect} />);
    await screen.findByRole("option", { name: "MSA / 8 Notices" });
    await user.selectOptions(screen.getByLabelText("Subject source"), "art-1");
    expect(onSelect).toHaveBeenCalledWith({ id: "art-1", type: "Article", label: "MSA / 8 Notices", quote_text: undefined });
  });
});
