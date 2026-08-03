// RED tests for the frontend jurisdiction controlled vocabulary (sprint
// 2026-08-02-us-state-law, ruling R5, gate G5/G7).
//
// `../jurisdictions` does not exist yet -- this whole file is RED via a
// module-resolution error until the Developer creates it (mirrors the
// backend RED test at backend/tests/unit/test_jurisdiction_vocabulary.py,
// which pins the SAME 54-code list -- this file's `EXPECTED_JURISDICTION_CODES`
// must be transcribed identically).
//
// Design call (R5's "how the frontend gets it" decision, stated here so
// the Developer doesn't have to re-derive it): the backend is the runtime
// source of truth via `GET /api/v1/jurisdictions` (see
// backend/tests/integration/test_jurisdiction_api_validation.py) -- this
// constants module is NOT a live fetch, it is a compile-time TypeScript
// literal union mirroring the same list, so `Assertion["jurisdiction"]`
// and form state can be statically typed. Drift between the two is
// caught by a SEPARATE contract test the Developer must add once the
// endpoint exists (comparing this module's list against a live/mocked
// fetch of `GET /api/v1/jurisdictions`) -- that contract test is out of
// scope for this RED-test commit (no endpoint to call against yet) and is
// listed as a follow-up acceptance criterion in the sprint contract's
// jurisdiction-vocabulary item, not written here.

import { describe, expect, it } from "vitest";

// RED: this module does not exist yet.
import { JURISDICTION_CODES, JURISDICTION_OPTIONS } from "../jurisdictions";

const US_STATE_POSTAL_CODES = (
  "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN " +
  "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA " +
  "WA WV WI WY"
).split(" ");

const EXPECTED_JURISDICTION_CODES = [
  "IL",
  ...US_STATE_POSTAL_CODES.map((code) => `US-${code}`),
  "US-DC",
  "US-PR",
  "US-FED",
];

describe("JURISDICTION_CODES", () => {
  it("matches the director's 54-code controlled vocabulary, in canonical order", () => {
    expect(EXPECTED_JURISDICTION_CODES).toHaveLength(54);
    expect(JURISDICTION_CODES).toEqual(EXPECTED_JURISDICTION_CODES);
  });

  it("has no duplicate codes", () => {
    expect(new Set(JURISDICTION_CODES).size).toBe(JURISDICTION_CODES.length);
  });
});

describe("JURISDICTION_OPTIONS", () => {
  it("mirrors STATUS_OPTIONS/ORIGIN_OPTIONS's {value,label} shape, one entry per code", () => {
    expect(JURISDICTION_OPTIONS).toHaveLength(JURISDICTION_CODES.length);
    for (const code of JURISDICTION_CODES) {
      expect(JURISDICTION_OPTIONS.some((option) => option.value === code)).toBe(true);
    }
  });

  it("gives every option a non-empty, human-readable label distinct from its raw code", () => {
    for (const option of JURISDICTION_OPTIONS) {
      expect(option.label.length).toBeGreaterThan(0);
    }
    // Spot checks: recognizable jurisdiction names, not raw codes echoed back.
    const byValue = Object.fromEntries(JURISDICTION_OPTIONS.map((o) => [o.value, o.label]));
    expect(byValue["IL"].toLowerCase()).toContain("israel");
    expect(byValue["US-DE"].toLowerCase()).toContain("delaware");
    expect(byValue["US-FED"].toLowerCase()).toContain("federal");
  });
});
