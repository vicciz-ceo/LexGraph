// KnowledgeBasePage — the active matter's assertion catalog: accepted
// assertions by default, any review status through the Status filter. It
// doubles as the global search results: the topbar search navigates to
// /knowledge?q=…, which searches every status the viewer can see. Adapted from
// the Stitch "knowledge_base" screen per the design review: no fabricated
// domains, "votes" become strength ratings, and user ratings / model
// confidence / review status stay three separate signals.
//
// A matter can hold tens of thousands of pipeline-written assertions, so the
// table shows one server page at a time (limit/offset), and each row carries
// its rating aggregate: a page costs one request (audit finding ui:1).

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import "../styles/pages/knowledge-base.css";

import { api } from "../api/client";
import { formatInstantDate, instantToIso } from "../api/datetime";
import type {
  AssertionList,
  AssertionListItem,
  AssertionListParams,
  AssertionOrigin,
  AssertionStatus,
} from "../api/types";
import { Icon } from "../app/icons";
import type { IconName } from "../app/icons";
import { Link, useHashLocation } from "../app/router";
import { useActiveSession } from "../app/session";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";

const DEBOUNCE_MS = 250;
/** Rows per table page. */
const PAGE_SIZE = 50;
/** Rows per request while exporting: the list endpoint's largest limit. */
const EXPORT_PAGE_SIZE = 500;

const STATUS_OPTIONS: { value: AssertionStatus | ""; label: string }[] = [
  { value: "accepted", label: "Accepted" },
  { value: "", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "proposed", label: "Proposed" },
  { value: "revision_requested", label: "Revision requested" },
  { value: "disputed", label: "Disputed" },
  { value: "rejected", label: "Rejected" },
  { value: "superseded", label: "Superseded" },
  { value: "withdrawn", label: "Withdrawn" },
];

/** The plain Knowledge Base is the accepted catalog; a search from the
 * topbar (a `?q=` URL) spans every status the viewer can see (ui:22). */
function defaultStatusFor(urlQ: string): AssertionStatus | "" {
  return urlQ === "" ? "accepted" : "";
}

const ORIGIN_OPTIONS: { value: AssertionOrigin | ""; label: string }[] = [
  { value: "", label: "All origins" },
  { value: "user_suggested", label: "Colleague" },
  { value: "model_suggested", label: "AI-deduced" },
  { value: "system_generated", label: "System" },
];

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "proposition", label: "Proposition A–Z" },
  { value: "assertion_type", label: "Type" },
  { value: "-average_rating", label: "Highest average rating" },
  { value: "-rating_count", label: "Most ratings" },
];

/** Orders by colleagues' ratings, which spec §17 requires to be labelled as
 * user opinion rather than legal authority. */
const RATING_SORTS = new Set(["-average_rating", "-rating_count"]);

const ORIGIN_CHIPS: Record<
  AssertionOrigin,
  { label: string; className: string; icon: IconName }
> = {
  user_suggested: { label: "Colleague", className: "chip chip--user", icon: "person" },
  model_suggested: { label: "AI-deduced", className: "chip chip--model", icon: "robot" },
  system_generated: { label: "System", className: "chip chip--system", icon: "settings" },
};

const EVIDENCE_LABELS: Record<string, string> = {
  evidenced: "Evidenced",
  unsupported: "Unsupported",
  awaiting_evidence: "Awaiting evidence",
};

/** Standing bands worth showing next to a proposed status badge. */
const STANDING_BANDS = new Set(["weak", "probable", "strong"]);

/** What a search covers, e.g. "across all statuses" or "in Accepted · AI-deduced". */
function searchScope(
  status: AssertionStatus | "",
  origin: AssertionOrigin | "",
  jurisdiction: string,
): string {
  const label = (options: { value: string; label: string }[], value: string) =>
    options.find((option) => option.value === value)?.label ?? value;
  const parts = [
    status === "" ? "across all statuses" : `in ${label(STATUS_OPTIONS, status)}`,
  ];
  if (origin) parts.push(label(ORIGIN_OPTIONS, origin));
  if (jurisdiction) parts.push(label(JURISDICTION_OPTIONS, jurisdiction));
  return parts.join(" · ");
}

function titleCase(value: string): string {
  const label = value.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

/** Offset of the last page that holds rows of a `total`-row result set. */
function lastPageOffset(total: number): number {
  return Math.max(0, Math.floor((total - 1) / PAGE_SIZE) * PAGE_SIZE);
}

/** A cell a spreadsheet application would evaluate as a formula: one that
 * starts with =, +, - or @ (also after leading whitespace, which some
 * importers trim) or with a tab or carriage return. Propositions are free
 * contributor text, so the export must never hand one over as a formula. */
const FORMULA_TRIGGER = /^(?:[\t\r]|\s*[=+\-@])/;

function csvCell(value: string): string {
  // A leading apostrophe makes spreadsheets read the cell as text (OWASP
  // "CSV injection"). Quoting alone does not: a quoted field is unquoted
  // before it is evaluated.
  const text = FORMULA_TRIGGER.test(value) ? `'${value}` : value;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

const CSV_HEADER = [
  "Proposition",
  "Type",
  "Jurisdiction",
  "Origin",
  "Status",
  "Standing",
  "Evidence",
  "Avg rating",
  "Ratings",
  "Updated",
];

function csvLine(assertion: AssertionListItem): string {
  const summary = assertion.ratings_summary ?? null;
  return [
    assertion.proposition,
    assertion.assertion_type,
    assertion.jurisdiction ?? "",
    ORIGIN_CHIPS[assertion.origin].label,
    assertion.status,
    assertion.standing,
    assertion.evidence_status,
    summary ? summary.average.toFixed(2) : "",
    String(summary?.count ?? 0),
    instantToIso(assertion.updated_at),
  ]
    .map(csvCell)
    .join(",");
}

interface ExportRun {
  cancelled: boolean;
}

/** Every match of `filters`, EXPORT_PAGE_SIZE rows per request; null if cancelled. */
async function fetchEveryMatch(
  matterId: string,
  filters: AssertionListParams,
  run: ExportRun,
  onProgress: (done: number, total: number) => void,
): Promise<AssertionListItem[] | null> {
  const rows: AssertionListItem[] = [];
  const seen = new Set<string>();
  let offset = 0;
  for (;;) {
    const page = await api.listAssertions(matterId, {
      ...filters,
      limit: EXPORT_PAGE_SIZE,
      offset,
    });
    if (run.cancelled) return null;
    for (const item of page.items) {
      // A row created mid-export shifts later pages by one; write it once.
      if (!seen.has(item.id)) {
        seen.add(item.id);
        rows.push(item);
      }
    }
    offset += page.items.length;
    onProgress(rows.length, page.total);
    if (page.items.length < EXPORT_PAGE_SIZE || offset >= page.total) return rows;
  }
}

function downloadCsv(rows: AssertionListItem[], matterId: string): void {
  const csv = [CSV_HEADER.join(","), ...rows.map(csvLine)].join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `lexgraph-assertions-${matterId}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function KnowledgeBasePage() {
  const { currentMatter } = useActiveSession();
  const matterId = currentMatter.id;
  const location = useHashLocation();
  const urlQ = location.query.get("q") ?? "";

  const [q, setQ] = useState(urlQ);
  const [debouncedQ, setDebouncedQ] = useState(urlQ);
  const [status, setStatus] = useState<AssertionStatus | "">(() => defaultStatusFor(urlQ));
  const [origin, setOrigin] = useState<AssertionOrigin | "">("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [data, setData] = useState<AssertionList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [exportProgress, setExportProgress] = useState<{ done: number; total: number } | null>(
    null,
  );
  const [exportError, setExportError] = useState<string | null>(null);
  const exportRun = useRef<ExportRun | null>(null);

  // The topbar search navigates to /knowledge?q=…; when the URL already is
  // that, AppShell re-dispatches hashchange. Either way `location` gets a new
  // identity, and the URL's search is applied afresh, replacing any in-page
  // refinement, so the same topbar query always gives the same results. The
  // first render already follows the URL.
  const [searchNonce, setSearchNonce] = useState(0);
  const mountLocation = useRef(location);
  useEffect(() => {
    if (location === mountLocation.current) return;
    setQ(urlQ);
    setDebouncedQ(urlQ);
    setStatus(defaultStatusFor(urlQ));
    setOrigin("");
    setJurisdiction("");
    setSearchNonce((nonce) => nonce + 1);
  }, [location, urlQ]);

  // Debounce in-page typing before it hits the API.
  useEffect(() => {
    if (q === debouncedQ) return;
    const timer = window.setTimeout(() => setDebouncedQ(q), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [q, debouncedQ]);

  const filters = useMemo<AssertionListParams>(() => {
    const params: AssertionListParams = { sort };
    if (debouncedQ) params.q = debouncedQ;
    if (status) params.status = status;
    if (origin) params.origin = origin;
    if (jurisdiction) params.jurisdiction = jurisdiction;
    return params;
  }, [debouncedQ, status, origin, jurisdiction, sort]);

  // A page offset belongs to one result set (matter + search + filters +
  // sort, and each topbar submit). Any change starts over at the first page:
  // the reset is stored during this render (React re-renders before
  // committing), so no request goes out for a stale offset, and returning to
  // an earlier filter value does not bring back its old page either.
  const resultKey = `${matterId}|${searchNonce}|${JSON.stringify(filters)}`;
  const [paging, setPaging] = useState({ resultKey, offset: 0 });
  if (paging.resultKey !== resultKey) setPaging({ resultKey, offset: 0 });
  const offset = paging.resultKey === resultKey ? paging.offset : 0;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.listAssertions(matterId, { ...filters, limit: PAGE_SIZE, offset }).then(
      (result) => {
        if (cancelled) return;
        // Rows can leave the result set while someone pages (reviewed or
        // edited elsewhere); past the end, show the last page that exists.
        if (result.items.length === 0 && result.total > 0 && offset > 0) {
          setPaging({ resultKey, offset: lastPageOffset(result.total) });
          return;
        }
        setData({ ...result, offset: result.offset ?? offset });
        setLoading(false);
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load assertions");
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [matterId, filters, resultKey, offset, reloadNonce]);

  // Leaving the page or switching matter abandons a running export.
  useEffect(
    () => () => {
      if (exportRun.current) exportRun.current.cancelled = true;
      exportRun.current = null;
      setExportProgress(null);
    },
    [matterId],
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const shownOffset = data?.offset ?? 0;
  const firstShown = shownOffset + 1;
  const lastShown = shownOffset + items.length;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const goToOffset = (next: number) =>
    setPaging({ resultKey, offset: Math.min(Math.max(0, next), lastPageOffset(total)) });

  const exportCsv = async () => {
    if (exportRun.current) return;
    const run: ExportRun = { cancelled: false };
    exportRun.current = run;
    setExportError(null);
    setExportProgress({ done: 0, total });
    try {
      const rows = await fetchEveryMatch(matterId, filters, run, (done, of) => {
        if (!run.cancelled) setExportProgress({ done, total: of });
      });
      if (rows !== null && !run.cancelled) downloadCsv(rows, matterId);
    } catch (err: unknown) {
      if (!run.cancelled) {
        setExportError(err instanceof Error ? err.message : "the server did not respond");
      }
    } finally {
      if (exportRun.current === run) {
        exportRun.current = null;
        setExportProgress(null);
      }
    }
  };

  const cancelExport = () => {
    if (exportRun.current) exportRun.current.cancelled = true;
    exportRun.current = null;
    setExportProgress(null);
  };

  const ratingCell = (assertion: AssertionListItem): ReactNode => {
    const summary = assertion.ratings_summary ?? null;
    if (summary === null || summary.count === 0) {
      return <span className="muted">—</span>;
    }
    return (
      <span className="kb-rating">
        avg {summary.average.toFixed(1)} · {summary.count}{" "}
        {summary.count === 1 ? "rating" : "ratings"}
      </span>
    );
  };

  return (
    <div className="kb">
      <header className="page-header">
        <div>
          <h1 className="page-header__title">
            Knowledge Base
            {data !== null && (
              <span className="page-header__count">{formatCount(data.total)}</span>
            )}
          </h1>
          <p className="page-header__subtitle">
            Legal assertions for {currentMatter.name} — review status, evidence, and
            community strength ratings.
          </p>
        </div>
      </header>

      <div className="kb-toolbar">
        <div className="kb-toolbar__search">
          <Icon name="search" size={16} />
          <input
            type="search"
            className="input"
            placeholder="Search assertions…"
            aria-label="Search assertions"
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />
        </div>
        <label className="kb-control">
          <span>Status</span>
          <select
            className="select"
            value={status}
            onChange={(event) => setStatus(event.target.value as AssertionStatus | "")}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="kb-control">
          <span>Origin</span>
          <select
            className="select"
            value={origin}
            onChange={(event) => setOrigin(event.target.value as AssertionOrigin | "")}
          >
            {ORIGIN_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="kb-control">
          <span>Jurisdiction</span>
          <select
            className="select"
            value={jurisdiction}
            onChange={(event) => setJurisdiction(event.target.value)}
          >
            <option value="">All jurisdictions</option>
            {JURISDICTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="kb-control">
          <span>Sort</span>
          <select
            className="select"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="kb-export">
          {exportProgress !== null && (
            <>
              <span className="kb-export__status" role="status">
                Exporting {formatCount(exportProgress.done)} of{" "}
                {formatCount(exportProgress.total)}…
              </span>
              <button
                type="button"
                className="btn btn--sm btn--secondary"
                aria-label="Cancel export"
                onClick={cancelExport}
              >
                Cancel
              </button>
            </>
          )}
          <button
            type="button"
            className="btn btn--secondary"
            title="Download every assertion that matches the search and filters"
            onClick={() => void exportCsv()}
            disabled={total === 0 || exportProgress !== null}
          >
            Export CSV
          </button>
        </div>
      </div>

      {debouncedQ !== "" && (
        <p className="kb-results">
          Results for <strong>“{debouncedQ}”</strong> {searchScope(status, origin, jurisdiction)}
        </p>
      )}
      {RATING_SORTS.has(sort) && (
        <p className="kb-sort-note">
          Ordered by colleagues' 1–5 strength ratings: user opinion, not legal authority
          or review status. Unrated assertions come last.
        </p>
      )}

      {exportError !== null && (
        <div className="error-banner" role="alert">
          CSV export failed: {exportError}
        </div>
      )}

      {error !== null && (
        <div className="error-banner" role="alert">
          {error}{" "}
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => setReloadNonce((nonce) => nonce + 1)}
          >
            Retry
          </button>
        </div>
      )}

      {loading && data === null ? (
        <div className="loading">Loading assertions…</div>
      ) : items.length === 0 ? (
        error === null && (
          <div className="empty-state">
            <p className="empty-state__title">No assertions found</p>
            <p>
              {debouncedQ !== ""
                ? `Nothing matches “${debouncedQ}” with the current filters.`
                : "Try widening the status or origin filters."}
            </p>
          </div>
        )
      ) : (
        <div className={loading ? "card kb-card kb-card--loading" : "card kb-card"} aria-busy={loading}>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Assertion</th>
                  <th>Origin</th>
                  <th>Status</th>
                  <th>Evidence</th>
                  <th>Ratings</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {items.map((assertion) => {
                  const chip = ORIGIN_CHIPS[assertion.origin];
                  const showStanding =
                    assertion.status === "proposed" &&
                    STANDING_BANDS.has(assertion.standing);
                  return (
                    <tr
                      key={assertion.id}
                      className={
                        assertion.status === "superseded"
                          ? "kb-row--superseded"
                          : undefined
                      }
                    >
                      <td className="kb-cell-assertion">
                        <Link
                          to={`/assertions/${assertion.id}`}
                          className="kb-proposition"
                        >
                          {assertion.proposition}
                        </Link>
                        <div className="kb-sub">
                          {assertion.assertion_type}
                          {assertion.jurisdiction !== null &&
                            ` · ${assertion.jurisdiction}`}
                        </div>
                      </td>
                      <td>
                        <span className={chip.className}>
                          <Icon name={chip.icon} size={13} />
                          {chip.label}
                        </span>
                        {assertion.origin === "model_suggested" &&
                          assertion.confidence !== null && (
                            <span className="kb-confidence">
                              {Math.round(assertion.confidence * 100)}% model
                              confidence
                            </span>
                          )}
                      </td>
                      <td>
                        <div className="kb-badges">
                          <span className={`badge badge--${assertion.status}`}>
                            {titleCase(assertion.status)}
                          </span>
                          {showStanding && (
                            <span className={`badge badge--${assertion.standing}`}>
                              {titleCase(assertion.standing)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`kb-evidence kb-evidence--${assertion.evidence_status}`}
                        >
                          {EVIDENCE_LABELS[assertion.evidence_status] ??
                            titleCase(assertion.evidence_status)}
                        </span>
                      </td>
                      <td>{ratingCell(assertion)}</td>
                      <td className="kb-date">{formatInstantDate(assertion.updated_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="kb-tablefoot">
            <span>
              Showing {formatCount(firstShown)}–{formatCount(lastShown)} of{" "}
              {formatCount(total)} assertions
            </span>
            {total > PAGE_SIZE && (
              <nav className="kb-pager" aria-label="Knowledge Base pages">
                <button
                  type="button"
                  className="btn btn--sm btn--secondary"
                  onClick={() => goToOffset(shownOffset - PAGE_SIZE)}
                  disabled={loading || shownOffset === 0}
                >
                  Previous
                </button>
                <span className="kb-pager__page">
                  Page {formatCount(Math.floor(shownOffset / PAGE_SIZE) + 1)} of{" "}
                  {formatCount(pageCount)}
                </span>
                <button
                  type="button"
                  className="btn btn--sm btn--secondary"
                  onClick={() => goToOffset(shownOffset + PAGE_SIZE)}
                  disabled={loading || lastShown >= total}
                >
                  Next
                </button>
              </nav>
            )}
            <span className="kb-legend">
              Community strength ratings — independent of review status and model
              confidence.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
