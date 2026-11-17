// Evidence selector (spec §2, §6, §8, §10): lists attached passages with
// their role and lets a permitted member attach a real source passage of
// the matter, found with the source search, under any of the six evidence
// roles, or remove one after confirming (findings ui:15, pipeline:8).
//
// The selector used to build `sourceSpanId: "search:<term>"` from free text
// (or "" with no text) and offer only two roles; the API rejects such ids
// with 422, so nothing attached through it could ever be saved. These
// tests pin real span ids from the search instead.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../api/client", () => ({
  api: { sources: vi.fn() },
}));

import { api } from "../../api/client";
import { AssertionEvidenceSelector } from "../AssertionEvidenceSelector";
import type { AssertionEvidenceItem } from "../AssertionEvidenceSelector";

const mockedApi = vi.mocked(api);

const evidence: AssertionEvidenceItem[] = [
  { id: "e1", sourceSpanId: "s1", evidenceRole: "supports", quote: "text A", documentTitle: "MSA", addedBy: "Grace Hopper" },
  { id: "e2", sourceSpanId: "s2", evidenceRole: "contradicts", quote: "text B" },
];

async function openAttachForm() {
  fireEvent.click(screen.getByRole("button", { name: "Attach evidence" }));
  await screen.findByRole("option", { name: /Notification within 72 hours/ });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.sources.mockResolvedValue({
    items: [
      { id: "span-7", document_title: "DPA", quote_text: "Notification within 72 hours of discovery." },
      { id: "s1", document_title: "MSA", quote_text: "text A" },
    ],
    total: 2,
  });
});

describe("AssertionEvidenceSelector", () => {
  it("lists existing evidence with its role", () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={evidence} onAdd={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByText(/text A/)).toBeInTheDocument();
    expect(screen.getByText(/supports/i)).toBeInTheDocument();
    expect(screen.getByText(/text B/)).toBeInTheDocument();
    expect(screen.getByText(/contradicts/i)).toBeInTheDocument();
    expect(screen.getByText("added by Grace Hopper")).toBeInTheDocument();
    // A passage is named by its document, never by its span id.
    expect(screen.getByText("MSA")).toBeInTheDocument();
    expect(screen.getByText("Quoted source")).toBeInTheDocument();
    expect(screen.queryByText("s1")).not.toBeInTheDocument();
  });

  it("supports adding supporting evidence from a real source passage", async () => {
    const onAdd = vi.fn();
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={onAdd} onRemove={vi.fn()} />);
    await openAttachForm();

    const attach = screen.getByRole("button", { name: "Attach selected passage" });
    // Nothing is attached before a passage is chosen.
    expect(attach).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Source passage"), { target: { value: "span-7" } });
    expect(screen.getByLabelText("Evidence role")).toHaveValue("supports");
    fireEvent.click(attach);

    expect(onAdd).toHaveBeenCalledWith({
      sourceSpanId: "span-7",
      evidenceRole: "supports",
      quote: "Notification within 72 hours of discovery.",
    });
    expect(await screen.findByText("Evidence attached.")).toBeInTheDocument();
  });

  it("supports adding contradicting evidence", async () => {
    const onAdd = vi.fn();
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={onAdd} onRemove={vi.fn()} />);
    await openAttachForm();

    fireEvent.change(screen.getByLabelText("Source passage"), { target: { value: "span-7" } });
    fireEvent.change(screen.getByLabelText("Evidence role"), { target: { value: "contradicts" } });
    fireEvent.click(screen.getByRole("button", { name: "Attach selected passage" }));

    expect(onAdd).toHaveBeenCalledWith(
      expect.objectContaining({ sourceSpanId: "span-7", evidenceRole: "contradicts" }),
    );
  });

  it("offers the six evidence roles the API accepts", async () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    await openAttachForm();

    const options = within(screen.getByLabelText("Evidence role")).getAllByRole("option");
    expect(options.map((option) => (option as HTMLOptionElement).value)).toEqual([
      "supports",
      "contradicts",
      "contextualizes",
      "qualifies",
      "primary_basis",
      "secondary_basis",
    ]);
  });

  it("does not attach a passage again with the role it already has", async () => {
    const onAdd = vi.fn();
    render(<AssertionEvidenceSelector matterId="m-1" evidence={evidence} onAdd={onAdd} onRemove={vi.fn()} />);
    await openAttachForm();

    fireEvent.change(screen.getByLabelText("Source passage"), { target: { value: "s1" } });
    expect(screen.getByRole("button", { name: "Attach selected passage" })).toBeDisabled();
    expect(screen.getByText("This passage is already attached with this role.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Evidence role"), { target: { value: "qualifies" } });
    fireEvent.click(screen.getByRole("button", { name: "Attach selected passage" }));
    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ sourceSpanId: "s1", evidenceRole: "qualifies" }));
  });

  it("keeps the form and shows the reason when attaching fails", async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error("source span belongs to another matter"));
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={onAdd} onRemove={vi.fn()} />);
    await openAttachForm();

    fireEvent.change(screen.getByLabelText("Source passage"), { target: { value: "span-7" } });
    fireEvent.click(screen.getByRole("button", { name: "Attach selected passage" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("source span belongs to another matter");
    expect(screen.getByLabelText("Source passage")).toHaveValue("span-7");
  });

  it("supports removing an evidence entry after confirming", async () => {
    const onRemove = vi.fn();
    render(<AssertionEvidenceSelector matterId="m-1" evidence={evidence} onAdd={vi.fn()} onRemove={onRemove} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    expect(onRemove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Remove evidence" }));
    expect(onRemove).toHaveBeenCalledWith("e1");
    expect(await screen.findByText("Evidence removed.")).toBeInTheDocument();
  });

  it("explains why an item cannot be removed and disables its Remove", () => {
    render(
      <AssertionEvidenceSelector
        matterId="m-1"
        evidence={evidence}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        removalBlockedReason={(item) => (item.id === "e1" ? "Keep one supporting passage." : null)}
      />,
    );
    const [first, second] = screen.getAllByRole("button", { name: "Remove" });
    expect(first).toBeDisabled();
    expect(second).toBeEnabled();
    expect(screen.getByText("Keep one supporting passage.")).toBeInTheDocument();
  });

  it("supports searching for source spans to attach", async () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    // The search only loads once the user asks to attach evidence.
    expect(mockedApi.sources).not.toHaveBeenCalled();
    await openAttachForm();

    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "notification" } });
    expect(screen.getByLabelText(/search/i)).toHaveValue("notification");
    await waitFor(() =>
      expect(mockedApi.sources).toHaveBeenCalledWith("m-1", "source-spans", "notification", 0),
    );
  });

  it("is read-only without onAdd and onRemove", () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={evidence} />);
    expect(screen.getByText(/text A/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows the caller's empty message", () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} emptyMessage="Nothing attached yet." />);
    expect(screen.getByText("Nothing attached yet.")).toBeInTheDocument();
  });

  it("lets the user indicate that further evidence is needed, when the caller stores it", () => {
    const onChange = vi.fn();
    render(
      <AssertionEvidenceSelector
        matterId="m-1"
        evidence={[]}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        onNeedsFurtherEvidenceChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText(/further evidence needed/i));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("offers no further-evidence flag that nothing would store", () => {
    render(<AssertionEvidenceSelector matterId="m-1" evidence={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.queryByLabelText(/further evidence needed/i)).not.toBeInTheDocument();
  });
});
