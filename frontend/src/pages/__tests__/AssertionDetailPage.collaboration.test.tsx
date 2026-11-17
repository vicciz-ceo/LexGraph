// AssertionDetailPage — the collaboration capabilities the spec documents
// are reachable from the detail page and gated like the API (findings ui:15,
// pipeline:8): attaching and removing evidence after creation (edit rule),
// editing, deleting and replying to comments (own comments,
// assertion:comment), comparing revisions (spec §3) and superseding an
// accepted assertion (reviewers). The api module and session hooks are
// mocked; every test renders the real page.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Assertion,
  AssertionComment,
  AssertionDetail,
  Evidence,
  MatterMember,
  MatterRoleName,
  RatingSummary,
  Revision,
} from "../../api/types";

vi.mock("../../api/client", () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      detail: string,
    ) {
      super(detail);
      this.name = "ApiError";
    }
  }
  return {
    ApiError,
    api: {
      getAssertion: vi.fn(),
      relatedAssertions: vi.fn(),
      ratingSummary: vi.fn(),
      listRatings: vi.fn(),
      history: vi.fn(),
      listMatterMembers: vi.fn(),
      putRating: vi.fn(),
      deleteRating: vi.fn(),
      addComment: vi.fn(),
      updateComment: vi.fn(),
      deleteComment: vi.fn(),
      addEvidence: vi.fn(),
      removeEvidence: vi.fn(),
      sources: vi.fn(),
      listAssertions: vi.fn(),
      supersedeAssertion: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
    },
  };
});

const sessionState = vi.hoisted(() => ({ role: "reviewer" as string }));

vi.mock("../../app/session", () => {
  const user = { id: "u-1", email: "ada@example.com", display_name: "Ada Lovelace" };
  const matter = { id: "m-1", name: "Acme acquisition", repository_id: "repo-1", organization_id: "org-1" };
  const active = () => ({
    user,
    currentMatter: { ...matter, role: sessionState.role },
    role: sessionState.role,
    matters: [{ ...matter, role: sessionState.role }],
  });
  return {
    useActiveSession: active,
    useSession: () => ({
      session: active(),
      selectMatter: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    }),
  };
});

import { ApiError, api } from "../../api/client";
import { AssertionDetailPage } from "../AssertionDetailPage";

const mockedApi = vi.mocked(api);

const PROPOSITION = "Termination for convenience requires payment of a termination fee.";

function revision(number: number, overrides: Partial<Revision> = {}): Revision {
  return {
    id: `rev-${number}`,
    assertion_id: "a-1",
    revision_number: number,
    proposition: `Text of revision ${number}.`,
    proposition_raw: null,
    assertion_type: "APPLIES_TO",
    subject_entity: { type: "Document", id: "doc-1" },
    object_entity: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    revision_reason: null,
    edited_by_user_id: "u-2",
    created_at: `2026-07-0${number}T12:00:00Z`,
    ...overrides,
  };
}

function evidence(overrides: Partial<Evidence> = {}): Evidence {
  return {
    id: "ev-1",
    assertion_id: "a-1",
    source_span_id: "span-1",
    quote_text: "Either party may terminate on 90 days' notice.",
    document_title: "Master Services Agreement",
    evidence_role: "supports",
    added_by_user_id: "u-2",
    created_at: "2026-07-01T10:05:00Z",
    ...overrides,
  };
}

function comment(overrides: Partial<AssertionComment> = {}): AssertionComment {
  return {
    id: "c-1",
    assertion_id: "a-1",
    user_id: "u-1",
    parent_comment_id: null,
    comment_text: "Check clause 12.",
    comment_text_raw: "Check <clause 12>.",
    created_at: "2026-07-03T08:00:00Z",
    updated_at: "2026-07-03T08:00:00Z",
    deleted_at: null,
    ...overrides,
  };
}

function detail(overrides: Partial<AssertionDetail> = {}): AssertionDetail {
  return {
    id: "a-1",
    organization_id: "org-1",
    repository_id: "repo-1",
    matter_id: "m-1",
    assertion_type: "APPLIES_TO",
    proposition: PROPOSITION,
    proposition_raw: null,
    subject_entity: { type: "Document", id: "doc-1", label: "Master Services Agreement" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u-1",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-10T09:00:00Z",
    submitted_at: "2026-07-02T10:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    evidence: [evidence()],
    ratings_summary: null,
    comments: [],
    revision_history: [revision(1)],
    ...overrides,
  };
}

function summary(revisionNumber: number, overrides: Partial<RatingSummary> = {}): RatingSummary {
  return {
    count: 0,
    average: null,
    median: null,
    distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
    assertion_id: "a-1",
    assertion_revision_id: `rev-${revisionNumber}`,
    assertion_revision_number: revisionNumber,
    current_user_rating: null,
    rationale_count: 0,
    ...overrides,
  };
}

function listed(id: string, proposition: string, overrides: Partial<Assertion> = {}): Assertion {
  const { evidence: _e, ratings_summary: _r, comments: _c, revision_history: _h, ...base } = detail();
  return { ...base, id, proposition, status: "accepted", standing: "accepted", ...overrides };
}

function member(id: string, display_name: string, role: MatterRoleName): MatterMember {
  return { user: { id, email: `${id}@example.com`, display_name }, role };
}

const ROSTER: MatterMember[] = [
  member("u-1", "Ada Lovelace", "contributor"),
  member("u-2", "Grace Hopper", "contributor"),
  member("u-3", "Riva Reviewer", "reviewer"),
  member("u-4", "Alan Admin", "admin"),
];

async function renderPage() {
  const view = render(<AssertionDetailPage assertionId="a-1" />);
  await screen.findByText(PROPOSITION);
  return view;
}

function card(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionState.role = "contributor";
  mockedApi.getAssertion.mockResolvedValue(detail());
  mockedApi.relatedAssertions.mockResolvedValue([]);
  mockedApi.ratingSummary.mockImplementation(async (_id: string, rev: number) => summary(rev));
  mockedApi.listRatings.mockResolvedValue([]);
  mockedApi.history.mockResolvedValue([]);
  mockedApi.listMatterMembers.mockResolvedValue(ROSTER);
  mockedApi.addComment.mockResolvedValue({} as never);
  mockedApi.updateComment.mockResolvedValue({} as never);
  mockedApi.deleteComment.mockResolvedValue(undefined);
  mockedApi.addEvidence.mockResolvedValue({} as never);
  mockedApi.removeEvidence.mockResolvedValue(undefined);
  mockedApi.sources.mockResolvedValue({
    items: [
      {
        id: "span-9",
        document_title: "Master Services Agreement",
        quote_text: "A termination fee equal to three months of fees applies.",
      },
    ],
    total: 1,
  });
  mockedApi.listAssertions.mockResolvedValue({ items: [], total: 0 });
  mockedApi.supersedeAssertion.mockResolvedValue({} as never);
});

// --- Evidence after creation ----------------------------------------------------

describe("attaching and removing evidence (ui:15, pipeline:8)", () => {
  it("lets the author of an unreviewed assertion attach a real source passage with a role", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({ evidence: [], evidence_status: "awaiting_evidence" }),
    );
    await renderPage();
    const evidenceCard = card("Evidence");

    // Collapsed by default: the source search only loads on request.
    expect(mockedApi.sources).not.toHaveBeenCalled();
    fireEvent.click(within(evidenceCard).getByRole("button", { name: "Attach evidence" }));

    const attach = within(evidenceCard).getByRole("button", { name: "Attach selected passage" });
    expect(attach).toBeDisabled();
    await within(evidenceCard).findByRole("option", { name: /A termination fee equal to three months/ });
    fireEvent.change(within(evidenceCard).getByLabelText("Source passage"), {
      target: { value: "span-9" },
    });
    fireEvent.change(within(evidenceCard).getByLabelText("Evidence role"), {
      target: { value: "primary_basis" },
    });
    fireEvent.click(attach);

    await waitFor(() =>
      expect(mockedApi.addEvidence).toHaveBeenCalledWith("a-1", "span-9", "primary_basis"),
    );
    expect(mockedApi.sources).toHaveBeenCalledWith("m-1", "source-spans", "", 0);
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    expect(await within(evidenceCard).findByText("Evidence attached.")).toBeInTheDocument();
  });

  it("offers all six roles and says which ones count as support", async () => {
    await renderPage();
    const evidenceCard = card("Evidence");
    fireEvent.click(within(evidenceCard).getByRole("button", { name: "Attach evidence" }));

    const roles = within(within(evidenceCard).getByLabelText("Evidence role")).getAllByRole("option");
    expect(roles.map((option) => option.textContent)).toEqual([
      "Supports",
      "Contradicts",
      "Contextualizes",
      "Qualifies",
      "Primary basis",
      "Secondary basis",
    ]);
    expect(
      within(evidenceCard).getByText(/Supports, Primary basis and Secondary basis count as supporting evidence/),
    ).toBeInTheDocument();
  });

  it("does not attach the same passage twice with the same role", async () => {
    await renderPage();
    const evidenceCard = card("Evidence");
    mockedApi.sources.mockResolvedValue({
      items: [{ id: "span-1", document_title: "Master Services Agreement", quote_text: "Either party may terminate." }],
      total: 1,
    });
    fireEvent.click(within(evidenceCard).getByRole("button", { name: "Attach evidence" }));
    await within(evidenceCard).findByRole("option", { name: /Either party may terminate\./ });
    fireEvent.change(within(evidenceCard).getByLabelText("Source passage"), { target: { value: "span-1" } });

    expect(within(evidenceCard).getByRole("button", { name: "Attach selected passage" })).toBeDisabled();
    expect(within(evidenceCard).getByText("This passage is already attached with this role.")).toBeInTheDocument();

    fireEvent.change(within(evidenceCard).getByLabelText("Evidence role"), { target: { value: "qualifies" } });
    expect(within(evidenceCard).getByRole("button", { name: "Attach selected passage" })).toBeEnabled();
  });

  it("removes evidence after a confirmation and re-reads the record", async () => {
    await renderPage();
    const row = within(card("Evidence")).getByText("Either party may terminate on 90 days' notice.").closest("li") as HTMLElement;

    fireEvent.click(within(row).getByRole("button", { name: "Remove" }));
    expect(mockedApi.removeEvidence).not.toHaveBeenCalled();
    fireEvent.click(within(row).getByRole("button", { name: "Remove evidence" }));

    await waitFor(() => expect(mockedApi.removeEvidence).toHaveBeenCalledWith("a-1", "ev-1"));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    expect(await within(card("Evidence")).findByText("Evidence removed.")).toBeInTheDocument();
  });

  it("can cancel a removal", async () => {
    await renderPage();
    const row = within(card("Evidence")).getByText("Either party may terminate on 90 days' notice.").closest("li") as HTMLElement;

    fireEvent.click(within(row).getByRole("button", { name: "Remove" }));
    fireEvent.click(within(row).getByRole("button", { name: "Keep" }));

    expect(within(row).queryByRole("button", { name: "Remove evidence" })).not.toBeInTheDocument();
    expect(mockedApi.removeEvidence).not.toHaveBeenCalled();
  });

  it.each<[string, MatterRoleName, Partial<AssertionDetail>]>([
    ["a viewer", "viewer", {}],
    ["a contributor who is not the author", "contributor", { author_user_id: "u-2" }],
    ["the author once the assertion is accepted", "contributor", { status: "accepted", standing: "accepted" }],
    ["the author of a withdrawn assertion", "contributor", { status: "withdrawn", standing: "withdrawn" }],
  ])("offers no evidence controls to %s", async (_who, role, overrides) => {
    sessionState.role = role;
    mockedApi.getAssertion.mockResolvedValue(detail(overrides));
    await renderPage();
    const evidenceCard = card("Evidence");

    expect(within(evidenceCard).getByText("Either party may terminate on 90 days' notice.")).toBeInTheDocument();
    expect(within(evidenceCard).queryByRole("button", { name: "Attach evidence" })).not.toBeInTheDocument();
    expect(within(evidenceCard).queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("lets a reviewer curate evidence on someone else's accepted assertion, but keeps its last supporting passage", async () => {
    sessionState.role = "reviewer";
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        status: "accepted",
        standing: "accepted",
        author_user_id: "u-2",
        evidence: [
          evidence(),
          evidence({ id: "ev-2", source_span_id: "span-2", evidence_role: "contradicts", quote_text: "Unless the fee is waived." }),
        ],
      }),
    );
    await renderPage();
    const evidenceCard = card("Evidence");

    expect(within(evidenceCard).getByRole("button", { name: "Attach evidence" })).toBeInTheDocument();
    const supporting = within(evidenceCard).getByText("Either party may terminate on 90 days' notice.").closest("li") as HTMLElement;
    expect(within(supporting).getByRole("button", { name: "Remove" })).toBeDisabled();
    expect(
      within(supporting).getByText(/An accepted assertion keeps at least one supporting passage/),
    ).toBeInTheDocument();
    const contradicting = within(evidenceCard).getByText("Unless the fee is waived.").closest("li") as HTMLElement;
    expect(within(contradicting).getByRole("button", { name: "Remove" })).toBeEnabled();
  });

  it("shows the server's reason when the API refuses, and re-reads the record", async () => {
    mockedApi.removeEvidence.mockRejectedValue(
      new ApiError(403, "Only the author of an unreviewed assertion or a reviewer may modify it"),
    );
    await renderPage();
    const row = within(card("Evidence")).getByText("Either party may terminate on 90 days' notice.").closest("li") as HTMLElement;

    fireEvent.click(within(row).getByRole("button", { name: "Remove" }));
    fireEvent.click(within(row).getByRole("button", { name: "Remove evidence" }));

    const alert = await within(card("Evidence")).findByRole("alert");
    expect(alert).toHaveTextContent("Only the author of an unreviewed assertion or a reviewer may modify it");
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });
});

// --- Comments ------------------------------------------------------------------

describe("editing, deleting and replying to comments (ui:15, pipeline:8)", () => {
  const thread = [
    comment(),
    comment({ id: "c-2", user_id: "u-3", comment_text: "Agreed; cite the fee clause.", comment_text_raw: "Agreed; cite the fee clause." }),
  ];

  it("offers Edit and Delete on the user's own comments only", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    await renderPage();

    const own = screen.getByTestId("comment-c-1");
    const other = screen.getByTestId("comment-c-2");
    expect(within(own).getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(within(own).getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(within(other).queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(within(other).queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("edits with the exact authored text prefilled and re-reads the record", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    await renderPage();
    const own = screen.getByTestId("comment-c-1");

    fireEvent.click(within(own).getByRole("button", { name: "Edit" }));
    const box = within(own).getByLabelText("Edit comment");
    expect(box).toHaveValue("Check <clause 12>.");
    // Unchanged text is not a new version of the comment.
    expect(within(own).getByRole("button", { name: "Save comment" })).toBeDisabled();
    fireEvent.change(box, { target: { value: "Check <clause 12> and Annex 2." } });
    fireEvent.click(within(own).getByRole("button", { name: "Save comment" }));

    await waitFor(() =>
      expect(mockedApi.updateComment).toHaveBeenCalledWith("a-1", "c-1", "Check <clause 12> and Annex 2."),
    );
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(within(own).queryByLabelText("Edit comment")).not.toBeInTheDocument());
  });

  it("keeps the edit open with the server's reason when the edit is refused", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    mockedApi.updateComment.mockRejectedValue(
      new ApiError(422, "comment_text must contain text other than whitespace or markup"),
    );
    await renderPage();
    const own = screen.getByTestId("comment-c-1");

    fireEvent.click(within(own).getByRole("button", { name: "Edit" }));
    fireEvent.change(within(own).getByLabelText("Edit comment"), { target: { value: "<b></b>" } });
    fireEvent.click(within(own).getByRole("button", { name: "Save comment" }));

    expect(await within(own).findByRole("alert")).toHaveTextContent(
      "comment_text must contain text other than whitespace or markup",
    );
    expect(within(own).getByLabelText("Edit comment")).toHaveValue("<b></b>");
  });

  it("deletes after a confirmation and re-reads the record", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    await renderPage();
    const own = screen.getByTestId("comment-c-1");

    fireEvent.click(within(own).getByRole("button", { name: "Delete" }));
    expect(mockedApi.deleteComment).not.toHaveBeenCalled();
    fireEvent.click(within(own).getByRole("button", { name: "Delete comment" }));

    await waitFor(() => expect(mockedApi.deleteComment).toHaveBeenCalledWith("a-1", "c-1"));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("posts a reply to the comment it answers", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    await renderPage();
    const other = screen.getByTestId("comment-c-2");

    fireEvent.click(within(other).getByRole("button", { name: "Reply" }));
    fireEvent.change(within(other).getByLabelText("Reply to Riva Reviewer"), {
      target: { value: "Done, see clause 14.2." },
    });
    fireEvent.click(within(other).getByRole("button", { name: "Post reply" }));

    await waitFor(() =>
      expect(mockedApi.addComment).toHaveBeenCalledWith("a-1", "Done, see clause 14.2.", "c-2"),
    );
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("nests replies under the comment they answer and keeps a removed parent's place", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        comments: [
          comment({ id: "c-1", user_id: "u-2", deleted_at: "2026-07-04T08:00:00Z", comment_text: "", comment_text_raw: null }),
          comment({ id: "c-2", user_id: "u-3", comment_text: "Unrelated top-level remark.", created_at: "2026-07-03T09:00:00Z" }),
          comment({ id: "c-3", user_id: "u-4", parent_comment_id: "c-1", comment_text: "Replying to the removed one.", created_at: "2026-07-03T10:00:00Z" }),
        ],
      }),
    );
    await renderPage();

    const removed = screen.getByTestId("comment-c-1");
    expect(within(removed).getByText("[comment removed]")).toBeInTheDocument();
    // The reply is rendered inside its parent's thread, before the later top-level comment.
    const reply = within(removed).getByTestId("comment-c-3");
    // A removed comment takes no reply: the only Reply in its thread is the live reply's.
    const replyButtons = within(removed).getAllByRole("button", { name: "Reply" });
    expect(replyButtons).toHaveLength(1);
    expect(reply).toContainElement(replyButtons[0]);
    const order = screen.getAllByTestId(/^comment-c-/).map((node) => node.dataset.testid);
    expect(order).toEqual(["comment-c-1", "comment-c-3", "comment-c-2"]);
  });

  it("marks comments by reviewers and admins", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        comments: [
          ...thread,
          comment({ id: "c-4", user_id: "u-4", comment_text: "Admin note.", comment_text_raw: "Admin note." }),
        ],
      }),
    );
    await renderPage();

    expect(within(screen.getByTestId("comment-c-1")).queryByText("Reviewer")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("comment-c-2")).getByText("Reviewer")).toBeInTheDocument();
    expect(within(screen.getByTestId("comment-c-4")).getByText("Admin")).toBeInTheDocument();
  });

  it("says when a comment was edited", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({ comments: [comment({ updated_at: "2026-07-05T08:00:00Z" })] }),
    );
    await renderPage();

    expect(within(screen.getByTestId("comment-c-1")).getByText("(edited)")).toBeInTheDocument();
  });

  it("offers a viewer no comment actions, not even on comments they wrote", async () => {
    sessionState.role = "viewer";
    mockedApi.getAssertion.mockResolvedValue(detail({ comments: thread }));
    await renderPage();

    const own = screen.getByTestId("comment-c-1");
    expect(within(own).getByText("Check clause 12.")).toBeInTheDocument();
    for (const name of ["Edit", "Delete", "Reply"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    expect(screen.queryByLabelText("Add a comment")).not.toBeInTheDocument();
  });
});

// --- Revision comparison -----------------------------------------------------------

describe("comparing revisions (ui:15, pipeline:8; spec §3)", () => {
  function twoRevisions() {
    return detail({
      current_revision_number: 2,
      jurisdiction: "IL",
      revision_history: [
        revision(1, { proposition: "Termination for convenience is free.", revision_reason: null }),
        revision(2, {
          proposition: PROPOSITION,
          proposition_raw: "Termination for convenience requires payment of a <termination fee>.",
          jurisdiction: "IL",
          revision_reason: "Cite the fee clause",
          edited_by_user_id: "u-3",
        }),
      ],
    });
  }

  it("offers no comparison for a single revision", async () => {
    await renderPage();

    const activity = card("Activity");
    expect(within(activity).queryByRole("button", { name: "Compare selected revisions" })).not.toBeInTheDocument();
    expect(within(activity).queryByLabelText(/Select revision 1 for comparison/)).not.toBeInTheDocument();
  });

  it("compares two selected revisions side by side and names the fields that changed", async () => {
    mockedApi.getAssertion.mockResolvedValue(twoRevisions());
    mockedApi.ratingSummary.mockImplementation(async (_id: string, rev: number) =>
      rev === 1 ? summary(1, { count: 2, average: 4.5, median: 4.5 }) : summary(2),
    );
    await renderPage();
    const activity = card("Activity");

    const compare = within(activity).getByRole("button", { name: "Compare selected revisions" });
    expect(compare).toBeDisabled();
    fireEvent.click(within(activity).getByLabelText("Select revision 1 for comparison"));
    fireEvent.click(within(activity).getByLabelText("Select revision 2 for comparison"));
    fireEvent.click(compare);

    const comparison = await screen.findByRole("region", { name: "Revision comparison" });
    expect(within(comparison).getByText("Termination for convenience is free.")).toBeInTheDocument();
    expect(
      within(comparison).getByText("Termination for convenience requires payment of a <termination fee>."),
    ).toBeInTheDocument();
    expect(within(comparison).getByText("Changed: proposition, jurisdiction.")).toBeInTheDocument();
    const jurisdictionRow = within(comparison).getByRole("row", { name: /Jurisdiction/ });
    expect(within(jurisdictionRow).getByText("Changed")).toBeInTheDocument();
    expect(within(jurisdictionRow).getByText("IL")).toBeInTheDocument();
    const typeRow = within(comparison).getByRole("row", { name: /Assertion type/ });
    expect(within(typeRow).queryByText("Changed")).not.toBeInTheDocument();
    expect(within(comparison).getByText("Riva Reviewer")).toBeInTheDocument();
    // Each side's ratings stay with their revision.
    expect(await within(comparison).findByText(/4\.5 average from 2 ratings for this revision/)).toBeInTheDocument();
    expect(within(comparison).getByText("This revision has not yet been rated.")).toBeInTheDocument();
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a-1", 1);

    fireEvent.click(screen.getByRole("button", { name: "Close comparison" }));
    expect(screen.queryByRole("region", { name: "Revision comparison" })).not.toBeInTheDocument();
  });

  it("keeps every revision's text visible in Activity", async () => {
    mockedApi.getAssertion.mockResolvedValue(twoRevisions());
    await renderPage();

    const activity = card("Activity");
    expect(within(activity).getByText("Termination for convenience is free.")).toBeInTheDocument();
    expect(within(activity).getByText("Cite the fee clause")).toBeInTheDocument();
    expect(within(activity).getByRole("button", { name: "Load ratings for revision 1" })).toBeInTheDocument();
  });
});

// --- Supersede ------------------------------------------------------------------

describe("superseding an accepted assertion (ui:15, pipeline:8)", () => {
  function accepted(overrides: Partial<AssertionDetail> = {}) {
    return detail({ status: "accepted", standing: "accepted", author_user_id: "u-2", ...overrides });
  }

  it("is offered only to reviewers and admins, and only on accepted assertions", async () => {
    sessionState.role = "contributor";
    mockedApi.getAssertion.mockResolvedValue(accepted());
    const view = await renderPage();
    expect(screen.queryByRole("button", { name: /Mark as superseded/ })).not.toBeInTheDocument();
    view.unmount();

    sessionState.role = "reviewer";
    mockedApi.getAssertion.mockResolvedValue(detail({ status: "proposed" }));
    const proposed = await renderPage();
    expect(screen.queryByRole("button", { name: /Mark as superseded/ })).not.toBeInTheDocument();
    proposed.unmount();

    sessionState.role = "admin";
    mockedApi.getAssertion.mockResolvedValue(accepted());
    await renderPage();
    expect(screen.getByRole("button", { name: /Mark as superseded/ })).toBeInTheDocument();
  });

  it("supersedes with a related accepted assertion, never itself or an unaccepted one", async () => {
    sessionState.role = "reviewer";
    mockedApi.getAssertion.mockResolvedValue(accepted());
    mockedApi.relatedAssertions.mockResolvedValue([
      { assertion_id: "a-9", match_kind: "similar", score: 0.8, proposition: "A newer accepted reading.", status: "accepted" },
      { assertion_id: "a-8", match_kind: "similar", score: 0.7, proposition: "A proposed reading.", status: "proposed" },
    ]);
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    const panel = card("Supersede");
    expect(within(panel).queryByLabelText("A proposed reading.")).not.toBeInTheDocument();
    const submit = within(panel).getByRole("button", { name: "Supersede with selected assertion" });
    expect(submit).toBeDisabled();
    fireEvent.click(within(panel).getByLabelText("A newer accepted reading."));
    fireEvent.click(submit);

    await waitFor(() => expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-9", 1, "accepted"));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("searches the matter's accepted assertions for the replacement", async () => {
    sessionState.role = "reviewer";
    mockedApi.getAssertion.mockResolvedValue(accepted());
    mockedApi.listAssertions.mockResolvedValue({
      items: [
        listed("a-1", PROPOSITION),
        listed("a-7", "The fee is three months of charges."),
        listed("a-6", "A withdrawn reading.", { status: "withdrawn", standing: "withdrawn" }),
        listed("a-5", "Points back at this one.", { superseded_by_assertion_id: "a-1" }),
      ],
      total: 4,
    });
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    const panel = card("Supersede");
    fireEvent.change(within(panel).getByLabelText("Search accepted assertions"), { target: { value: "fee" } });

    const option = await within(panel).findByLabelText("The fee is three months of charges.");
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      q: "fee",
      status: "accepted",
      sort: "-created_at",
      limit: 25,
    });
    expect(within(panel).queryByLabelText(PROPOSITION)).not.toBeInTheDocument();
    expect(within(panel).queryByLabelText("A withdrawn reading.")).not.toBeInTheDocument();
    expect(within(panel).queryByLabelText("Points back at this one.")).not.toBeInTheDocument();
    fireEvent.click(option);
    fireEvent.click(within(panel).getByRole("button", { name: "Supersede with selected assertion" }));

    await waitFor(() => expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-7", 1, "accepted"));
  });

  it("shows the server's reason when the supersede is refused", async () => {
    sessionState.role = "reviewer";
    mockedApi.getAssertion.mockResolvedValue(accepted());
    mockedApi.relatedAssertions.mockResolvedValue([
      { assertion_id: "a-9", match_kind: "similar", score: 0.8, proposition: "A newer accepted reading.", status: "accepted" },
    ]);
    mockedApi.supersedeAssertion.mockRejectedValue(
      new ApiError(422, "superseding assertion leads back to this assertion (supersede cycle)"),
    );
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    const panel = card("Supersede");
    fireEvent.click(within(panel).getByLabelText("A newer accepted reading."));
    fireEvent.click(within(panel).getByRole("button", { name: "Supersede with selected assertion" }));

    expect(await within(panel).findByRole("alert")).toHaveTextContent("supersede cycle");
  });

  it("links a superseded assertion to the assertion that replaced it", async () => {
    mockedApi.getAssertion.mockImplementation(async (id: string) =>
      id === "a-9"
        ? detail({ id: "a-9", proposition: "A newer accepted reading.", status: "accepted", standing: "accepted" })
        : detail({ status: "superseded", standing: "superseded", superseded_by_assertion_id: "a-9" }),
    );
    await renderPage();

    const notice = await screen.findByText(/Superseded by/);
    const link = within(notice).getByRole("link", { name: "A newer accepted reading." });
    expect(link).toHaveAttribute("href", "#/assertions/a-9");
    expect(screen.queryByRole("button", { name: /Mark as superseded/ })).not.toBeInTheDocument();
  });

  it("still links the replacement when it cannot be loaded", async () => {
    mockedApi.getAssertion.mockImplementation(async (id: string) => {
      if (id === "a-9") throw new ApiError(404, "assertion not found");
      return detail({ status: "superseded", standing: "superseded", superseded_by_assertion_id: "a-9" });
    });
    await renderPage();

    const notice = await screen.findByText(/Superseded by/);
    expect(within(notice).getByRole("link", { name: "the superseding assertion" })).toHaveAttribute(
      "href",
      "#/assertions/a-9",
    );
  });
});
