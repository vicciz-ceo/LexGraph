// AssertionDetailPage — the page tells the truth about the record: who did
// what (ui:0, ui:14), which revision ratings belong to (ui:12), rating
// rationales (ui:16), a readable distribution (ui:29), entity and related
// labels instead of UUIDs (ui:30), links into another matter (ui:31 /
// review:11), the exact rationale on a strength-only update (review:7) and
// system-generated definition links (ui:4). The api module and session hooks
// are mocked; every test renders the real page.

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AssertionDetail,
  HistoryEvent,
  MatterMember,
  MatterMembership,
  MatterRoleName,
  Rating,
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
      putRating: vi.fn(),
      deleteRating: vi.fn(),
      addComment: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
      history: vi.fn(),
      listMatterMembers: vi.fn(),
    },
  };
});

const sessionState = vi.hoisted(() => ({
  role: "reviewer" as string,
  matterId: "m-1",
  matters: [] as { id: string; name: string; repository_id: string; organization_id: string; role: string }[],
  selectMatter: vi.fn(),
}));

vi.mock("../../app/session", () => {
  const user = { id: "u-1", email: "ada@example.com", display_name: "Ada Lovelace" };
  const active = () => {
    const matter =
      sessionState.matters.find((m) => m.id === sessionState.matterId) ?? sessionState.matters[0];
    return {
      user,
      currentMatter: { ...matter, role: sessionState.role },
      role: sessionState.role,
      matters: sessionState.matters,
    };
  };
  return {
    useActiveSession: active,
    useSession: () => ({
      session: active(),
      selectMatter: sessionState.selectMatter,
      signIn: vi.fn(),
      signOut: vi.fn(),
      refresh: vi.fn(),
    }),
  };
});

import { ApiError, api } from "../../api/client";
import { AssertionDetailPage } from "../AssertionDetailPage";

const mockedApi = vi.mocked(api);

function matter(id: string, name: string, role: MatterRoleName = "reviewer"): MatterMembership {
  return { id, name, repository_id: "repo-1", organization_id: "org-1", role };
}

function revision(number: number, overrides: Partial<Revision> = {}): Revision {
  return {
    id: `rev-${number}`,
    assertion_id: "a-1",
    revision_number: number,
    proposition: `Proposition text of revision ${number}.`,
    proposition_raw: null,
    assertion_type: "obligation",
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

const PROPOSITION = "Acme Corp must deliver audited financial statements by 31 March each year.";
const DOC_UUID = "61c95f7e-1a2b-4c3d-8e9f-0a1b2c3d4e5f";
const ARTICLE_UUID = "05cee0ec-500e-59c4-affe-907e5cebb5db";

function detail(overrides: Partial<AssertionDetail> = {}): AssertionDetail {
  return {
    id: "a-1",
    organization_id: "org-1",
    repository_id: "repo-1",
    matter_id: "m-1",
    assertion_type: "obligation",
    proposition: PROPOSITION,
    proposition_raw: null,
    subject_entity: { type: "Document", id: DOC_UUID, label: "Master Services Agreement" },
    object_entity: {
      type: "Article",
      id: ARTICLE_UUID,
      label: "Master Services Agreement / 8.4 Public-domain exception",
    },
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u-2",
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
    current_revision_number: 2,
    evidence_status: "evidenced",
    evidence: [
      {
        id: "ev-1",
        assertion_id: "a-1",
        source_span_id: "span-123",
        quote_text: "The tenant must deliver statements by 31 March.",
        document_title: "Master Services Agreement",
        evidence_role: "supports",
        added_by_user_id: "u-2",
        created_at: "2026-07-01T10:05:00Z",
      },
    ],
    ratings_summary: null,
    comments: [
      {
        id: "c-1",
        assertion_id: "a-1",
        user_id: "u-2",
        parent_comment_id: null,
        comment_text: "Please double-check the deadline.",
        comment_text_raw: null,
        created_at: "2026-07-03T08:00:00Z",
        updated_at: null,
        deleted_at: null,
      },
    ],
    revision_history: [revision(1), revision(2)],
    ...overrides,
  };
}

function summary(overrides: Partial<RatingSummary> = {}): RatingSummary {
  return {
    count: 0,
    average: null,
    median: null,
    distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
    assertion_id: "a-1",
    assertion_revision_id: "rev-2",
    assertion_revision_number: 2,
    current_user_rating: null,
    rationale_count: 0,
    ...overrides,
  };
}

function rating(overrides: Partial<Rating> = {}): Rating {
  return {
    id: "r-1",
    assertion_id: "a-1",
    assertion_revision_id: "rev-2",
    assertion_revision_number: 2,
    user_id: "u-3",
    strength: 4,
    rationale: null,
    rationale_raw: null,
    created_at: "2026-07-06T10:00:00Z",
    updated_at: "2026-07-06T10:00:00Z",
    ...overrides,
  };
}

function member(id: string, display_name: string, role: MatterRoleName): MatterMember {
  return { user: { id, email: `${id}@example.com`, display_name }, role };
}

const ROSTER: MatterMember[] = [
  member("u-1", "Ada Lovelace", "reviewer"),
  member("u-2", "Grace Hopper", "contributor"),
  member("u-3", "Riva Reviewer", "reviewer"),
];

function historyEvent(overrides: Partial<HistoryEvent>): HistoryEvent {
  return {
    id: "h-x",
    event_type: "assertion_created",
    actor_user_id: "u-2",
    timestamp: "2026-07-01T10:00:00Z",
    assertion_revision_number: 1,
    previous_value: null,
    new_value: null,
    correlation_id: null,
    ...overrides,
  };
}

/** Summaries per revision number; unknown revisions reject like a 404. */
function summariesByRevision(byRevision: Record<number, RatingSummary>) {
  mockedApi.ratingSummary.mockImplementation(async (_id: string, rev: number) => {
    const found = byRevision[rev];
    if (!found) throw new ApiError(404, "revision not found");
    return found;
  });
}

async function renderPage(id = "a-1") {
  const view = render(<AssertionDetailPage assertionId={id} />);
  await screen.findByText(PROPOSITION);
  return view;
}

function ratingsCard(): HTMLElement {
  return screen.getByRole("region", { name: "Ratings" });
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionState.role = "reviewer";
  sessionState.matterId = "m-1";
  sessionState.matters = [matter("m-1", "Acme acquisition"), matter("m-2", "Data Processing Addendum")];
  mockedApi.getAssertion.mockResolvedValue(detail());
  mockedApi.relatedAssertions.mockResolvedValue([]);
  summariesByRevision({ 1: summary({ assertion_revision_number: 1 }), 2: summary() });
  mockedApi.listRatings.mockResolvedValue([]);
  mockedApi.putRating.mockResolvedValue({} as Rating);
  mockedApi.deleteRating.mockResolvedValue(undefined);
  mockedApi.addComment.mockResolvedValue({} as never);
  mockedApi.acceptAssertion.mockResolvedValue({} as never);
  mockedApi.rejectAssertion.mockResolvedValue({} as never);
  mockedApi.disputeAssertion.mockResolvedValue({} as never);
  mockedApi.requestRevision.mockResolvedValue({} as never);
  mockedApi.history.mockResolvedValue([]);
  mockedApi.listMatterMembers.mockResolvedValue(ROSTER);
});

describe("people are named, never shown as user ids (ui:0)", () => {
  it("resolves the evidence adder, comment author and revision editor from the matter roster", async () => {
    await renderPage();

    expect(mockedApi.listMatterMembers).toHaveBeenCalledWith("m-1");
    expect(screen.getByText("added by Grace Hopper")).toBeInTheDocument();
    const comment = screen.getByText("Please double-check the deadline.").closest("li") as HTMLElement;
    expect(within(comment).getByText("Grace Hopper")).toBeInTheDocument();
    expect(within(comment).getByText("GH")).toBeInTheDocument();
    expect(screen.getAllByText(/Grace Hopper ·/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\bu-2\b/)).not.toBeInTheDocument();
  });

  it("labels someone who has left the matter as a former member", async () => {
    mockedApi.listMatterMembers.mockResolvedValue([member("u-1", "Ada Lovelace", "reviewer")]);
    await renderPage();

    expect(screen.getByText("added by Former member")).toBeInTheDocument();
    expect(screen.queryByText(/\bu-2\b/)).not.toBeInTheDocument();
  });

  it("falls back to a neutral label, not the id, when the roster cannot be loaded", async () => {
    mockedApi.listMatterMembers.mockRejectedValue(new Error("roster down"));
    await renderPage();

    expect(screen.getByText("added by Team member")).toBeInTheDocument();
    expect(screen.queryByText(/\bu-2\b/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("ratings recorded against a prior revision (ui:12)", () => {
  const priorNotice = /2 earlier ratings were recorded against prior revisions of this assertion\. Revision v2 has not been rated yet/;

  it("tells a reviewer, in the Ratings card and the Review card, that only a prior revision was rated", async () => {
    summariesByRevision({ 2: summary({ prior_revision_rating_count: 2 }) });
    await renderPage();

    expect(within(ratingsCard()).getByText(priorNotice)).toBeInTheDocument();
    expect(document.querySelector(".assertion-review-revision-notice")).not.toBeNull();
    // One summary request: the server counts the earlier revisions' ratings.
    expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(1);
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a-1", 2);
  });

  it("informs a contributor, who has no Review card, as well", async () => {
    sessionState.role = "contributor";
    summariesByRevision({ 2: summary({ prior_revision_rating_count: 2 }) });
    await renderPage();

    expect(within(ratingsCard()).getByText(priorNotice)).toBeInTheDocument();
  });

  it("names the current revision and uses the singular for one earlier rating", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({ current_revision_number: 3, revision_history: [revision(1), revision(2), revision(3)] }),
    );
    summariesByRevision({ 3: summary({ assertion_revision_number: 3, prior_revision_rating_count: 1 }) });
    await renderPage();

    expect(
      within(ratingsCard()).getByText(/^1 earlier rating was recorded against prior revisions.*Revision v3 has not been rated yet/),
    ).toBeInTheDocument();
  });

  it("shows no notice when no revision was ever rated", async () => {
    await renderPage();

    expect(screen.queryByText(/earlier rating/)).not.toBeInTheDocument();
    expect(document.querySelector(".assertion-review-revision-notice")).toBeNull();
  });

  it("shows no notice when the current revision is rated", async () => {
    summariesByRevision({
      2: summary({
        count: 1, average: 3, median: 3, prior_revision_rating_count: 2,
        distribution: { "1": 0, "2": 0, "3": 1, "4": 0, "5": 0 },
      }),
    });
    await renderPage();

    expect(screen.queryByText(/earlier rating/)).not.toBeInTheDocument();
    expect(document.querySelector(".assertion-review-revision-notice")).toBeNull();
  });

  it("never flashes the notice while removing the only rating of a never-revised assertion", async () => {
    const own = { strength: 4, rationale: null, rationale_raw: null, updated_at: "2026-07-06T10:00:00Z" };
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        current_revision_number: 1,
        revision_history: [revision(1)],
        ratings_summary: { assertion_id: "a-1", assertion_revision_id: "rev-1", average: 4, median: 4, count: 1, distribution: { "4": 1 } },
      }),
    );
    summariesByRevision({
      1: summary({ count: 1, average: 4, median: 4, current_user_rating: own, assertion_revision_number: 1 }),
    });
    await renderPage();

    let releaseDetail: (value: AssertionDetail) => void = () => {};
    mockedApi.getAssertion.mockImplementation(
      () => new Promise<AssertionDetail>((resolve) => { releaseDetail = resolve; }),
    );
    summariesByRevision({ 1: summary({ assertion_revision_number: 1 }) });
    fireEvent.click(screen.getByRole("button", { name: "Remove rating" }));
    await waitFor(() => expect(mockedApi.deleteRating).toHaveBeenCalledWith("a-1", 1));

    expect(screen.queryByText(/earlier rating/)).not.toBeInTheDocument();
    expect(document.querySelector(".assertion-review-revision-notice")).toBeNull();

    await act(async () => {
      releaseDetail(detail({ current_revision_number: 1, revision_history: [revision(1)], ratings_summary: null }));
    });
    await screen.findByText("Rating removed.");
    expect(screen.queryByText(/earlier rating/)).not.toBeInTheDocument();
  });

  it("says which revision the team ratings belong to", async () => {
    await renderPage();

    expect(within(ratingsCard()).getByText("Team ratings for revision v2 (current)")).toBeInTheDocument();
  });
});

describe("author, reviewer and review history (ui:14)", () => {
  it("names the author and shows no reviewer line before any review", async () => {
    await renderPage();

    expect(screen.getByText("Author: Grace Hopper")).toBeInTheDocument();
    expect(screen.queryByText(/Last reviewed by/)).not.toBeInTheDocument();
  });

  it("names the last reviewer and the decision date", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({ status: "accepted", standing: "accepted", reviewed_by: "u-3", reviewed_at: "2026-07-10T09:00:00Z" }),
    );
    await renderPage();

    expect(screen.getByText(/^Last reviewed by Riva Reviewer on Jul 10, 2026$/)).toBeInTheDocument();
  });

  it("lists review decisions newest first, with reviewer, revision, date and the full justification", async () => {
    mockedApi.history.mockResolvedValue([
      historyEvent({ id: "h-1", event_type: "assertion_created", actor_user_id: "u-2" }),
      historyEvent({ id: "h-2", event_type: "rating_created", actor_user_id: "u-3", new_value: "4" }),
      historyEvent({
        id: "h-3",
        event_type: "assertion.request_revision",
        actor_user_id: "u-3",
        timestamp: "2026-07-04T09:00:00Z",
        previous_value: "proposed",
        new_value: "revision_requested; comment=Cite clause 8.4; the term=defined there.",
      }),
      historyEvent({
        id: "h-4",
        event_type: "assertion.accept",
        actor_user_id: "u-1",
        timestamp: "2026-07-10T09:00:00Z",
        assertion_revision_number: 2,
        previous_value: "proposed",
        new_value: "accepted; acceptance_justification=Annex 2; see clause=8.4 for the carve-out.",
      }),
    ]);
    await renderPage();

    const card = screen.getByRole("region", { name: "Review history" });
    const items = within(card).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText("Accepted")).toBeInTheDocument();
    expect(within(items[0]).getByText("revision 2")).toBeInTheDocument();
    expect(within(items[0]).getByText(/^Ada Lovelace · /)).toBeInTheDocument();
    expect(
      within(items[0]).getByText("Justification: Annex 2; see clause=8.4 for the carve-out."),
    ).toBeInTheDocument();
    expect(within(items[1]).getByText("Revision requested")).toBeInTheDocument();
    expect(within(items[1]).getByText(/^Riva Reviewer · /)).toBeInTheDocument();
    expect(within(items[1]).getByText("Comment: Cite clause 8.4; the term=defined there.")).toBeInTheDocument();
    // Rating rows (per-user strengths) are not part of the review history.
    expect(within(card).queryByText(/rating/i)).not.toBeInTheDocument();
  });

  it("links a supersede decision to the successor instead of printing its id", async () => {
    mockedApi.history.mockResolvedValue([
      historyEvent({
        id: "h-5",
        event_type: "assertion.supersede",
        actor_user_id: "u-3",
        previous_value: "accepted",
        new_value: "superseded; superseded_by_assertion_id=5128af22-13d9-48e4-bafa-3c7c87f0d599",
      }),
    ]);
    await renderPage();

    const card = screen.getByRole("region", { name: "Review history" });
    const link = within(card).getByRole("link", { name: "the superseding assertion" });
    expect(link).toHaveAttribute("href", "#/assertions/5128af22-13d9-48e4-bafa-3c7c87f0d599");
    expect(within(card).queryByText(/5128af22/)).not.toBeInTheDocument();
  });

  it("has an empty state", async () => {
    await renderPage();

    const card = screen.getByRole("region", { name: "Review history" });
    expect(within(card).getByText("No review decisions recorded yet.")).toBeInTheDocument();
  });

  it("keeps the record usable when the history cannot be loaded", async () => {
    mockedApi.history.mockRejectedValue(new Error("history down"));
    await renderPage();

    expect(screen.getByText("Review history could not be loaded.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("re-reads the history after a review decision", async () => {
    await renderPage();
    expect(mockedApi.history).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => expect(mockedApi.history).toHaveBeenCalledTimes(2));
  });
});

describe("rating rationales (ui:16)", () => {
  it("shows a reviewer every rater's rationale and how many ratings have one", async () => {
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({ count: 2, average: 3.5, median: 3.5, rationale_count: 1, distribution: { "1": 0, "2": 0, "3": 1, "4": 1, "5": 0 } }),
    });
    mockedApi.listRatings.mockResolvedValue([
      rating({ id: "r-1", user_id: "u-3", strength: 4, rationale: "Verbatim in the survival clause." }),
      rating({ id: "r-2", user_id: "u-2", strength: 3, rationale: null }),
    ]);
    await renderPage();

    expect(mockedApi.listRatings).toHaveBeenCalledWith("a-1", 2);
    const card = ratingsCard();
    expect(within(card).getByText("1 of 2 ratings on this revision includes a rationale.")).toBeInTheDocument();
    const list = within(card).getByRole("list", { name: "Rating rationales" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(1);
    expect(within(items[0]).getByText("Riva Reviewer")).toBeInTheDocument();
    expect(within(items[0]).getByText(/4 — Strong/)).toBeInTheDocument();
    expect(within(items[0]).getByText("Verbatim in the survival clause.")).toBeInTheDocument();
  });

  it("shows a contributor only their own rationale and says who can read the others", async () => {
    sessionState.role = "contributor";
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({ count: 2, average: 3, median: 3, rationale_count: 2 }),
    });
    mockedApi.listRatings.mockResolvedValue([
      rating({ id: "r-1", user_id: "u-3", strength: 4, rationale: null }),
      rating({ id: "r-2", user_id: "u-1", strength: 2, rationale: "My own reading of clause 8." }),
    ]);
    await renderPage();

    const list = within(ratingsCard()).getByRole("list", { name: "Rating rationales" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(1);
    expect(within(items[0]).getByText("Ada Lovelace (you)")).toBeInTheDocument();
    expect(within(items[0]).getByText("My own reading of clause 8.")).toBeInTheDocument();
    expect(
      within(ratingsCard()).getByText("Other raters' rationales are visible to reviewers and admins."),
    ).toBeInTheDocument();
  });

  it("re-reads the rationales after the user saves a rating", async () => {
    await renderPage();
    expect(mockedApi.listRatings).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("radio", { name: "4 - Strong" }));
    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));

    await screen.findByText("Rating saved.");
    expect(mockedApi.listRatings).toHaveBeenCalledTimes(2);
  });

  it("renders markup in a rationale as inert text", async () => {
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({ count: 1, average: 4, median: 4, rationale_count: 1 }),
    });
    mockedApi.listRatings.mockResolvedValue([
      rating({ rationale: "<img src=x onerror=alert(1)> see clause 8" }),
    ]);
    const { container } = await renderPage();

    expect(screen.getByText("<img src=x onerror=alert(1)> see clause 8")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("keeps the page usable when the rationales cannot be loaded", async () => {
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({ count: 1, average: 4, median: 4, rationale_count: 1 }),
    });
    mockedApi.listRatings.mockRejectedValue(new Error("ratings down"));
    await renderPage();

    expect(within(ratingsCard()).getByText("Rating rationales could not be loaded.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a prior revision's rationales when its ratings are loaded under Activity", async () => {
    summariesByRevision({
      1: summary({ count: 1, average: 5, median: 5, rationale_count: 1, assertion_revision_number: 1 }),
      2: summary(),
    });
    mockedApi.listRatings.mockImplementation(async (_id: string, rev: number) =>
      rev === 1
        ? [rating({ assertion_revision_number: 1, user_id: "u-3", strength: 5, rationale: "Old text was explicit." })]
        : [],
    );
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Load ratings for revision 1" }));

    expect(await screen.findByText("Old text was explicit.")).toBeInTheDocument();
    expect(mockedApi.listRatings).toHaveBeenCalledWith("a-1", 1);
  });
});

describe("rating distribution (ui:29)", () => {
  it("names every bucket and its count separately", async () => {
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({ count: 2, average: 5, median: 5, distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 2 } }),
    });
    await renderPage();

    const buckets = within(ratingsCard()).getByRole("list", { name: /Rating distribution/ });
    const five = within(buckets).getByTestId("rating-distribution-bucket-5");
    expect(five).toHaveAccessibleName("5 (Very strong): 2 of 2 ratings");
    expect(within(five).getByText("Very strong")).toBeInTheDocument();
    expect(within(five).getByText("2")).toBeInTheDocument();
    expect(within(buckets).getByTestId("rating-distribution-bucket-1")).toHaveAccessibleName(
      "1 (Very weak): 0 of 2 ratings",
    );
  });

  it("states that ratings are individual assessments, not legal conclusions", async () => {
    await renderPage();

    expect(
      within(ratingsCard()).getByText(
        "Ratings reflect users' individual assessments and do not constitute formal legal conclusions.",
      ),
    ).toBeInTheDocument();
  });
});

describe("labels instead of UUIDs (ui:30)", () => {
  it("names the subject and object entities", async () => {
    await renderPage();

    expect(screen.getByText("Master Services Agreement / 8.4 Public-domain exception")).toBeInTheDocument();
    expect(screen.queryByText(DOC_UUID)).not.toBeInTheDocument();
    expect(screen.queryByText(ARTICLE_UUID)).not.toBeInTheDocument();
  });

  it("marks an unresolved legacy reference as such instead of printing the UUID", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        subject_entity: { type: "Provision", id: "713c042d-eb60-4375-a566-a62fcd0716d0", label: null },
        object_entity: null,
      }),
    );
    await renderPage();

    expect(screen.getByText("External reference")).toBeInTheDocument();
    expect(screen.getByText("713c042d")).toBeInTheDocument();
    expect(screen.queryByText("713c042d-eb60-4375-a566-a62fcd0716d0")).not.toBeInTheDocument();
  });

  it("links an Assertion subject by its proposition", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({ subject_entity: { type: "Assertion", id: "a-7", label: "The cap excludes indemnities." } }),
    );
    await renderPage();

    expect(screen.getByRole("link", { name: /The cap excludes indemnities\./ })).toHaveAttribute(
      "href",
      "#/assertions/a-7",
    );
  });

  it("lists related assertions by proposition and status", async () => {
    mockedApi.relatedAssertions.mockResolvedValue([
      {
        assertion_id: "5728cea5-51bc-445a-b659-4e65b2bf79d2",
        match_kind: "similar",
        score: 0.57,
        proposition: "The liability cap equals the total fees paid under the agreement.",
        status: "superseded",
      },
    ]);
    await renderPage();

    const link = screen.getByRole("link", { name: "The liability cap equals the total fees paid under the agreement." });
    expect(link).toHaveAttribute("href", "#/assertions/5728cea5-51bc-445a-b659-4e65b2bf79d2");
    const item = link.closest("li") as HTMLElement;
    expect(within(item).getByText("Superseded")).toBeInTheDocument();
    expect(within(item).getByText("Similar proposition")).toBeInTheDocument();
    expect(screen.queryByText("5728cea5-51bc-445a-b659-4e65b2bf79d2")).not.toBeInTheDocument();
  });

  it("does not print a span id when an evidence source cannot be resolved", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      detail({
        evidence: [
          {
            id: "ev-9",
            assertion_id: "a-1",
            source_span_id: "48b08d35-e093-43f4-b497-03a27db18afd",
            quote_text: null,
            document_title: null,
            evidence_role: "supports",
            added_by_user_id: "u-2",
            created_at: "2026-07-01T10:05:00Z",
          },
        ],
      }),
    );
    await renderPage();

    expect(screen.getByText("Source span unavailable")).toBeInTheDocument();
    expect(screen.queryByText("48b08d35-e093-43f4-b497-03a27db18afd")).not.toBeInTheDocument();
  });
});

describe("links into another matter (ui:31, review:11)", () => {
  it("switches to the assertion's matter when the user belongs to it", async () => {
    sessionState.matterId = "m-2";
    sessionState.selectMatter.mockImplementation((id: string) => {
      sessionState.matterId = id;
    });
    const view = render(<AssertionDetailPage assertionId="a-1" />);

    await waitFor(() => expect(sessionState.selectMatter).toHaveBeenCalledWith("m-1"));
    expect(screen.queryByText("Assertion not found")).not.toBeInTheDocument();
    view.rerender(<AssertionDetailPage assertionId="a-1" />);

    await screen.findByText(PROPOSITION);
    expect(
      screen.getByText("Switched the active matter from Data Processing Addendum to Acme acquisition to show this assertion."),
    ).toBeInTheDocument();
  });

  it("offers to switch back, instead of switching on its own, after the user leaves the matter", async () => {
    const view = await renderPage();

    sessionState.matterId = "m-2";
    view.rerender(<AssertionDetailPage assertionId="a-1" />);

    expect(
      await screen.findByText("This assertion belongs to Acme acquisition, not the active matter Data Processing Addendum."),
    ).toBeInTheDocument();
    expect(sessionState.selectMatter).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Switch to Acme acquisition" }));
    expect(sessionState.selectMatter).toHaveBeenCalledWith("m-1");
  });

  it("explains a matter that is missing from the user's matter list", async () => {
    mockedApi.getAssertion.mockResolvedValue(detail({ matter_id: "m-9" }));
    render(<AssertionDetailPage assertionId="a-1" />);

    expect(await screen.findByText(/belongs to a matter that is not in your matter list/)).toBeInTheDocument();
    expect(sessionState.selectMatter).not.toHaveBeenCalled();
    expect(screen.queryByText("Assertion not found")).not.toBeInTheDocument();
  });

  it("tells a non-member the assertion is not available to them", async () => {
    mockedApi.getAssertion.mockRejectedValue(new ApiError(403, "no access to matter"));
    render(<AssertionDetailPage assertionId="a-1" />);

    expect(await screen.findByText("Assertion not available")).toBeInTheDocument();
    expect(screen.getByText(/belongs to a matter you are not a member of/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});

describe("the rationale survives a strength-only update (review:7)", () => {
  it("prefills the exact text and sends it back unchanged", async () => {
    const raw = "Compare <Annex 2> with clause 8.4";
    summariesByRevision({
      1: summary({ assertion_revision_number: 1 }),
      2: summary({
        count: 1,
        average: 3,
        median: 3,
        rationale_count: 1,
        current_user_rating: {
          strength: 3,
          rationale: "Compare  with clause 8.4",
          rationale_raw: raw,
          updated_at: "2026-07-06T10:00:00Z",
        },
      }),
    });
    await renderPage();

    expect(screen.getByLabelText("Rationale (optional)")).toHaveValue(raw);
    fireEvent.click(screen.getByRole("radio", { name: "4 - Strong" }));
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));

    await waitFor(() => expect(mockedApi.putRating).toHaveBeenCalledWith("a-1", 2, 4, raw));
  });
});

describe("system-generated definition links (ui:4)", () => {
  function systemRow(overrides: Partial<AssertionDetail> = {}): AssertionDetail {
    return detail({
      origin: "system_generated",
      status: "accepted",
      standing: "accepted",
      author_user_id: "u-3",
      confidence: 0.95,
      evidence: [],
      evidence_status: "awaiting_evidence",
      comments: [],
      current_revision_number: 1,
      revision_history: [],
      ...overrides,
    });
  }

  it("does not call an accepted pipeline link 'Awaiting evidence' or credit the person who ran the pipeline", async () => {
    mockedApi.getAssertion.mockResolvedValue(systemRow());
    await renderPage();

    expect(screen.queryByText("Awaiting evidence")).not.toBeInTheDocument();
    expect(screen.getByText("System-derived")).toBeInTheDocument();
    expect(screen.getByText(/generated this assertion automatically/)).toBeInTheDocument();
    expect(screen.getByText("Author: System (definition-linking pipeline)")).toBeInTheDocument();
    expect(screen.queryByText("Author: Riva Reviewer")).not.toBeInTheDocument();
    expect(screen.getByText("Pipeline run attributed to Riva Reviewer")).toBeInTheDocument();
    expect(screen.getByText("Pipeline confidence:", { exact: false })).toBeInTheDocument();
    // "Accepted" with no reviewer: say where the status came from.
    const reviewHistory = screen.getByRole("region", { name: "Review history" });
    expect(within(reviewHistory).getByText(/stores the links it generates as accepted/)).toBeInTheDocument();
  });

  it("does not offer a rating that cannot be saved, nor request ratings of an unrecorded revision", async () => {
    mockedApi.getAssertion.mockResolvedValue(systemRow());
    await renderPage();

    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    expect(within(ratingsCard()).getByText(/Revision v1 has no stored revision record, so it cannot be rated/)).toBeInTheDocument();
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
    expect(mockedApi.listRatings).not.toHaveBeenCalled();
    expect(screen.getByText(/System-generated assertions are created without a revision record/)).toBeInTheDocument();
  });

  it("shows the real evidence status once evidence is attached", async () => {
    mockedApi.getAssertion.mockResolvedValue(
      systemRow({ evidence_status: "evidenced", evidence: detail().evidence }),
    );
    await renderPage();

    expect(screen.getByText("Evidenced")).toBeInTheDocument();
    expect(screen.queryByText("System-derived")).not.toBeInTheDocument();
  });
});

describe("comment errors", () => {
  it("shows the server's reason next to the form and keeps the draft", async () => {
    mockedApi.addComment.mockRejectedValue(
      new ApiError(422, "comment_text must contain text other than whitespace or markup"),
    );
    await renderPage();

    fireEvent.change(screen.getByLabelText("Add a comment"), { target: { value: "<b></b>" } });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("comment_text must contain text other than whitespace or markup");
    expect(alert.closest(".adp-comment-form")).not.toBeNull();
    expect(screen.getByLabelText("Add a comment")).toHaveValue("<b></b>");
  });
});
