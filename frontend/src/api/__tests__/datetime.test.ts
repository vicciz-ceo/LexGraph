// Timestamps from the API must show the viewer's local time whatever the
// zone (audit finding ui:3). Each suite pins a zone: a UTC CI machine would
// hide an offset-less value being read as local time.

import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import {
  formatInstantDate,
  formatInstantDateTime,
  instantToIso,
  parseApiInstant,
} from "../datetime";

const UTC_MS = Date.UTC(2026, 10, 15, 20, 16, 17, 835);

function inZone(zone: string, body: () => void) {
  describe(`in ${zone}`, () => {
    beforeAll(() => {
      vi.stubEnv("TZ", zone);
    });
    afterAll(() => {
      vi.unstubAllEnvs();
    });
    body();
  });
}

for (const zone of ["UTC", "Asia/Tokyo", "America/New_York"]) {
  inZone(zone, () => {
    it("reads an offset-less API date-time as UTC, not local time", () => {
      expect(parseApiInstant("2026-11-15T20:16:17.835814")?.getTime()).toBe(UTC_MS);
      expect(parseApiInstant("2026-11-15 20:16:17.835814")?.getTime()).toBe(UTC_MS);
      expect(parseApiInstant("2026-11-15T20:16:17")?.getTime()).toBe(UTC_MS - 835);
    });

    it("keeps the offset a value already carries", () => {
      expect(parseApiInstant("2026-11-15T20:16:17.835814Z")?.getTime()).toBe(UTC_MS);
      expect(parseApiInstant("2026-11-15T20:16:17.835814+00:00")?.getTime()).toBe(UTC_MS);
      expect(parseApiInstant("2026-11-15T22:16:17.835+02:00")?.getTime()).toBe(UTC_MS);
      expect(parseApiInstant("2026-11-15T15:16:17.835-05:00")?.getTime()).toBe(UTC_MS);
    });

    it("returns null for a missing or unparseable value", () => {
      expect(parseApiInstant(null)).toBeNull();
      expect(parseApiInstant(undefined)).toBeNull();
      expect(parseApiInstant("")).toBeNull();
      expect(parseApiInstant("not a date")).toBeNull();
      expect(formatInstantDate(null)).toBe("—");
      expect(formatInstantDateTime("not a date")).toBe("—");
      expect(instantToIso("not a date")).toBe("not a date");
      expect(instantToIso(null)).toBe("");
    });

    it("formats naive and offset forms of one instant identically", () => {
      for (const naive of ["2026-11-15T20:16:17.835814", "2026-11-15 20:16:17.835814"]) {
        expect(formatInstantDate(naive)).toBe(formatInstantDate("2026-11-15T20:16:17.835814Z"));
        expect(formatInstantDateTime(naive)).toBe(
          formatInstantDateTime("2026-11-15T20:16:17.835814+00:00"),
        );
      }
      expect(instantToIso("2026-11-15T20:16:17.835814")).toBe("2026-11-15T20:16:17.835Z");
      expect(instantToIso("2026-11-15T22:16:17.835+02:00")).toBe("2026-11-15T20:16:17.835Z");
    });
  });
}

inZone("Asia/Tokyo", () => {
  it("shows the local calendar date, a day after the UTC one late in the UTC day", () => {
    // 20:16 UTC is 05:16 the next morning in Tokyo.
    expect(formatInstantDate("2026-11-15T20:16:17.835814", "en-US")).toBe("Nov 16, 2026");
    expect(
      formatInstantDateTime("2026-11-15T20:16:17.835814", "en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
    ).toBe("05:16");
  });
});

inZone("America/New_York", () => {
  it("shows the local calendar date, a day before the UTC one early in the UTC day", () => {
    // 02:00 UTC is 21:00 the previous evening in New York.
    expect(formatInstantDate("2026-11-16T02:00:00.000000", "en-US")).toBe("Nov 15, 2026");
  });
});
