// KnowledgeBasePage — the accepted-assertion catalog for the active matter,
// doubling as global search results (the topbar search navigates to
// /knowledge?q=…). Adapted from the Stitch "knowledge_base" screen per the
// design review: no fabricated domains, "votes" become strength ratings, and
// user ratings / model confidence / review status stay three separate signals.

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import "../styles/pages/knowledge-base.css";

import { api } from "../api/client";
import type {
  Assertion,
  AssertionList,
  AssertionListParams,
  AssertionOrigin,
  AssertionStatus,
  RatingSummary,
} from "../api/types";
import { Icon } from "../app/icons";
import type { IconName } from "../app/icons";
import { Link, useHashLocation } from "../app/router";
import { useActiveSession } from "../app/session";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";

const DEBOUNCE_MS = 250;

const STATUS_OPTIONS: { value: AssertionStatus | ""; label: string }[] = [
  { value: "accepted", label: "Accepted" },
  { value: "", label: "All statuses" },
  { value: "superseded", label: "Superseded" },
  { value: "disputed", label: "Disputed" },
  { value: "proposed", label: "Proposed" },
];

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
];

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

function summaryKey(assertion: Assertion): string {
  return `${assertion.id}:${assertion.current_revision_number}`;
}

function titleCase(value: string): string {
  const label = value.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function csvCell(value: string): string {
  return /[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

export function KnowledgeBasePage() {
  const { currentMatter } = useActiveSession();
  const matterId = currentMatter.id;
  const location = useHashLocation();
  const urlQ = location.query.get("q") ?? "";

  const [q, setQ] = useState(urlQ);
  const [debouncedQ, setDebouncedQ] = useState(urlQ);
  const [status, setStatus] = useState<AssertionStatus | "">("accepted");
  const [origin, setOrigin] = useState<AssertionOrigin | "">("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [data, setData] = useState<AssertionList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [summaries, setSummaries] = useState<Record<string, RatingSummary | null>>({});
  const requestedSummariesRef = useRef(new Set<string>());
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // The topbar search navigates to /knowledge?q=… — follow the URL, both on
  // first render and whenever the hash query changes afterwards.
  useEffect(() => {
    setQ(urlQ);
    setDebouncedQ(urlQ);
  }, [urlQ]);

  // Debounce in-page typing before it hits the API.
  useEffect(() => {
    if (q === debouncedQ) return;
    const timer = window.setTimeout(() => setDebouncedQ(q), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [q, debouncedQ]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params: AssertionListParams = { sort };
    if (debouncedQ) params.q = debouncedQ;
    if (status) params.status = status;
    if (origin) params.origin = origin;
    if (jurisdiction) params.jurisdiction = jurisdiction;
    api.listAssertions(matterId, params).then(
      (result) => {
        if (cancelled) return;
        setData(result);
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
  }, [matterId, debouncedQ, status, origin, jurisdiction, sort, reloadNonce]);

  // Ratings are per revision and not embedded in the list payload — fetch a
  // summary per visible row (cached by assertion + revision).
  useEffect(() => {
    if (!data) return;
    for (const assertion of data.items) {
      const revision = assertion.current_revision_number;
      if (revision === null) continue;
      const key = summaryKey(assertion);
      if (requestedSummariesRef.current.has(key)) continue;
      requestedSummariesRef.current.add(key);
      api.ratingSummary(assertion.id, revision).then(
        (summary) => {
          if (mountedRef.current) {
            setSummaries((prev) => ({ ...prev, [key]: summary }));
          }
        },
        () => {
          if (mountedRef.current) {
            setSummaries((prev) => ({ ...prev, [key]: null }));
          }
        },
      );
    }
  }, [data]);

  const items = data?.items ?? [];

  const exportCsv = () => {
    if (items.length === 0) return;
    const header = [
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
    const lines = items.map((assertion) => {
      const summary = summaries[summaryKey(assertion)];
      return [
        assertion.proposition,
        assertion.assertion_type,
        assertion.jurisdiction ?? "",
        ORIGIN_CHIPS[assertion.origin].label,
        assertion.status,
        assertion.standing,
        assertion.evidence_status,
        summary?.average != null ? summary.average.toFixed(2) : "",
        summary ? String(summary.count) : "",
        assertion.updated_at,
      ]
        .map(csvCell)
        .join(",");
    });
    const csv = [header.join(","), ...lines].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lexgraph-assertions-${matterId}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const ratingCell = (assertion: Assertion): ReactNode => {
    if (assertion.current_revision_number === null) {
      return <span className="muted">—</span>;
    }
    const key = summaryKey(assertion);
    if (!(key in summaries)) return <span className="muted">…</span>;
    const summary = summaries[key];
    if (!summary || summary.count === 0 || summary.average === null) {
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
            {data !== null && <span className="page-header__count">{data.total}</span>}
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
        <button
          type="button"
          className="btn btn--secondary kb-export"
          onClick={exportCsv}
          disabled={items.length === 0}
        >
          Export CSV
        </button>
      </div>

      {debouncedQ !== "" && (
        <p className="kb-results">
          Results for <strong>“{debouncedQ}”</strong>
        </p>
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
        <div className="card">
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
                      <td className="kb-date">{formatDate(assertion.updated_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="kb-tablefoot">
            <span>
              Showing {items.length} of {data?.total ?? items.length} assertions
            </span>
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
