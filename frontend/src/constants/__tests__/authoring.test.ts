// Helpers behind the Suggest Assertion flow and the revision editor:
// assertion-type vocabulary, 409 parsing, similar-assertion summaries,
// the further-evidence note and the default-jurisdiction preference.

import { afterEach, describe, expect, it, vi } from "vitest";

import { duplicateConflictOf, httpStatusOf, isStateConflict } from "../apiConflicts";
import {
  ASSERTION_TYPES,
  assertionTypeLabel,
  isRecognizedAssertionType,
  normalizeAssertionType,
} from "../assertionTypes";
import { defaultJurisdictionStorageKey, readDefaultJurisdiction } from "../preferences";
import {
  FURTHER_EVIDENCE_NOTE,
  SIMILAR_ASSERTIONS_DISPLAY_LIMIT,
  composeExplanation,
  summarizeSimilarAssertions,
} from "../suggestion";

class HttpError extends Error {
  constructor(public status: number, detail: string, public body: unknown = null) {
    super(detail);
  }
}

describe("assertion types", () => {
  it("mirrors the backend vocabulary in order", () => {
    expect(ASSERTION_TYPES).toEqual([
      "INTERPRETS",
      "CREATES_EXCEPTION_TO",
      "CONFLICTS_WITH",
      "MODIFIES",
      "APPLIES_TO",
      "RELEVANT_TO",
      "WEAKENS",
      "SUPPORTS",
      "SURVIVES_TERMINATION",
      "DISTINGUISHABLE_FROM",
      "USES_DEFINITION",
      "DERIVES_FROM_LAW",
    ]);
  });

  it.each([
    ["interprets", "INTERPRETS"],
    [" Cancelled by ", "CANCELLED_BY"],
    ["cancelled-by", "CANCELLED_BY"],
    ["cancelled / by!", "CANCELLED_BY"],
    ["__x__", "X"],
    ["חל על", "חל_על"],
    [" - ", ""],
  ])("normalizes %j to %j", (raw, expected) => {
    expect(normalizeAssertionType(raw)).toBe(expected);
  });

  it("recognizes only exact vocabulary entries and labels them", () => {
    expect(isRecognizedAssertionType("APPLIES_TO")).toBe(true);
    expect(isRecognizedAssertionType("applies_to")).toBe(false);
    expect(assertionTypeLabel("CREATES_EXCEPTION_TO")).toBe("Creates exception to");
  });
});

describe("409 parsing", () => {
  const duplicateDetail = "duplicate: an identical proposition already exists in this matter (assertion 1b2c-3)";

  it("reads the existing assertion id from the duplicate detail", () => {
    expect(duplicateConflictOf(new HttpError(409, duplicateDetail))).toEqual({ existingAssertionId: "1b2c-3" });
  });

  it("prefers a structured existing_assertion_id", () => {
    const error = new HttpError(409, "duplicate: an identical proposition", { existing_assertion_id: "a-7" });
    expect(duplicateConflictOf(error)).toEqual({ existingAssertionId: "a-7" });
  });

  it("does not treat other errors as duplicates", () => {
    expect(duplicateConflictOf(new HttpError(409, "assertion has been modified since expected_revision_number"))).toBeNull();
    expect(duplicateConflictOf(new HttpError(422, duplicateDetail))).toBeNull();
    expect(duplicateConflictOf(new Error(duplicateDetail))).toBeNull();
    expect(duplicateConflictOf(null)).toBeNull();
  });

  it("classifies state conflicts and statuses", () => {
    expect(isStateConflict(new HttpError(409, "cannot submit assertion in status 'withdrawn'"))).toBe(true);
    expect(isStateConflict(new HttpError(409, duplicateDetail))).toBe(false);
    expect(httpStatusOf(new HttpError(403, "no"))).toBe(403);
    expect(httpStatusOf("boom")).toBeNull();
  });
});

describe("similar-assertion summary", () => {
  it("keeps the new display fields and orders by score, then id", () => {
    const summary = summarizeSimilarAssertions({
      similar_assertions: [
        { assertion_id: "b", match_kind: "similar", score: 0.9, proposition: "B", status: "accepted", assertion_type: "APPLIES_TO" },
        { assertion_id: "a", match_kind: "similar", score: 0.9, proposition: "A", status: "proposed" },
        { assertion_id: "c", match_kind: "same_subject_type_object", score: 0.95, proposition: "C", status: "draft" },
      ],
      similar_assertions_total: 3,
      similar_assertions_truncated: false,
    });
    expect(summary.items.map((item) => item.id)).toEqual(["c", "a", "b"]);
    expect(summary.items[0]).toEqual({ id: "c", proposition: "C", status: "draft", matchKind: "same_subject_type_object", score: 0.95 });
    expect(summary.total).toBe(3);
  });

  it("tolerates an older backend: no text, no total, no cap, duplicates", () => {
    const raw = Array.from({ length: 25 }, (_, i) => ({ assertion_id: `x-${i}`, match_kind: "similar", score: 0.5 }));
    const summary = summarizeSimilarAssertions({ similar_assertions: [...raw, raw[0]] });
    expect(summary.items).toHaveLength(SIMILAR_ASSERTIONS_DISPLAY_LIMIT);
    expect(summary.items[0]).toEqual({ id: "x-0", proposition: "", status: null, matchKind: "similar", score: 0.5 });
    expect(summary.total).toBe(25);
    expect(summarizeSimilarAssertions({})).toEqual({ items: [], total: 0 });
  });

  it("reports the backend's total when the list was capped", () => {
    const capped = Array.from({ length: 20 }, (_, i) => ({ assertion_id: `y-${i}`, match_kind: "similar", score: 0.8 }));
    expect(summarizeSimilarAssertions({ similar_assertions: capped, similar_assertions_total: 42, similar_assertions_truncated: true }).total).toBe(42);
  });
});

describe("further-evidence note", () => {
  it("appends the note to the explanation, or stands alone", () => {
    expect(composeExplanation("  Because clause 8 says so. ", true)).toBe(`Because clause 8 says so.\n\n${FURTHER_EVIDENCE_NOTE}`);
    expect(composeExplanation("", true)).toBe(FURTHER_EVIDENCE_NOTE);
    expect(composeExplanation(" Reason ", false)).toBe("Reason");
    expect(composeExplanation("   ", false)).toBeNull();
  });
});

describe("default jurisdiction preference", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("uses the Profile page's storage key", () => {
    expect(defaultJurisdictionStorageKey("u-1")).toBe("lexgraph:default-jurisdiction:u-1");
  });

  it("returns a stored vocabulary code, and nothing for anything else", () => {
    window.localStorage.setItem("lexgraph:default-jurisdiction:u-1", "US-CA");
    window.localStorage.setItem("lexgraph:default-jurisdiction:u-2", "EU");
    expect(readDefaultJurisdiction("u-1")).toBe("US-CA");
    expect(readDefaultJurisdiction("u-2")).toBe("");
    expect(readDefaultJurisdiction("u-3")).toBe("");
  });

  it("survives unavailable storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    expect(readDefaultJurisdiction("u-1")).toBe("");
  });
});
