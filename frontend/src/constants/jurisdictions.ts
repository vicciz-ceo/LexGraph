// Jurisdiction controlled vocabulary — compile-time TS mirror (sprint
// 2026-08-02-us-state-law, ruling R5, gate G5/G7).
//
// Director decision #3 (2026-08-02, AskUserQuestion): jurisdiction is a
// FIXED controlled vocabulary — `IL` plus every US state's `US-<postal>`
// code, `US-DC`, `US-PR`, `US-FED`.
//
// The RUNTIME source of truth is the backend's `GET /api/v1/jurisdictions`
// (see backend/app/services/jurisdiction.py's `JURISDICTION_CODES`, and
// backend/tests/integration/test_jurisdiction_api_validation.py) — this
// module is a compile-time TypeScript literal mirror of the SAME 54-code
// list, in the SAME canonical order, so `Assertion["jurisdiction"]` and
// form state can be statically typed. A drift-detection contract test
// (comparing this list against a live/mocked fetch of the endpoint) is a
// documented follow-up, not part of this commit.

const US_STATE_POSTAL_CODES = (
  "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN " +
  "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA " +
  "WA WV WI WY"
).split(" ");

export const JURISDICTION_CODES: readonly string[] = [
  "IL",
  ...US_STATE_POSTAL_CODES.map((code) => `US-${code}`),
  "US-DC",
  "US-PR",
  "US-FED",
];

const US_STATE_NAMES: Record<string, string> = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
};

function labelFor(code: string): string {
  if (code === "IL") return "Israel";
  if (code === "US-DC") return "Washington, D.C.";
  if (code === "US-PR") return "Puerto Rico";
  if (code === "US-FED") return "U.S. Federal";
  const postal = code.slice("US-".length);
  const name = US_STATE_NAMES[postal];
  return name ? `${name} (${code})` : code;
}

export const JURISDICTION_OPTIONS: { value: string; label: string }[] = JURISDICTION_CODES.map(
  (code) => ({ value: code, label: labelFor(code) })
);
