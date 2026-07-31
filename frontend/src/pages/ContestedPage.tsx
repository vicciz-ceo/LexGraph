// ContestedPage — adjudication queue for status=disputed assertions.
//
// A reviewer marks an assertion disputed elsewhere (review queue / detail
// page); everything disputed in the current matter lands here for a final
// ruling. The three signals stay strictly separate per the platform spec:
// user strength ratings (1-5 aggregate), model confidence (only for
// AI-deduced assertions), and review status. Ratings never decide the
// outcome — the reviewer's adjudication does.

import { Fragment, useEffect, useRef, useState } from "react";

import "../styles/pages/contested.css";

import { ApiError, api } from "../api/client";
import type { Assertion, Evidence, RatingSummary } from "../api/types";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";

const ORIGIN_CHIPS: Record<Assertion["origin"], { className: string; label: string }> = {
  user_suggested: { className: "chip chip--user", label: "Colleague" },
  model_suggested: { className: "chip chip--model", label: "AI-deduced" },
  system_generated: { className: "chip chip--system", label: "System" },
};

const EVIDENCE_BADGES: Record<Assertion["evidence_status"], { className: string; label: string }> = {
  evidenced: { className: "badge badge--accepted", label: "Evidenced" },
  unsupported: { className: "badge badge--rejected", label: "Unsupported" },
  awaiting_evidence: { className: "badge badge--pending", label: "Awaiting evidence" },
};

function evidenceRoleClass(role: string): string {
  if (role === "supports") return "badge badge--accepted";
  if (role === "contradicts") return "badge badge--rejected";
  return "badge badge--neutral";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Compact weak/probable/strong strength bar for a queue row. */
function StrengthCell({ summary }: { summary: RatingSummary | null | undefined }) {
  if (summary === undefined) return <span className="muted">…</span>;
  if (summary === null || summary.count === 0) return <span className="muted">—</span>;

  const d = summary.distribution;
  const weak = (d["1"] ?? 0) + (d["2"] ?? 0);
  const probable = d["3"] ?? 0;
  const strong = (d["4"] ?? 0) + (d["5"] ?? 0);
  const total = weak + probable + strong;
  if (total === 0) return <span className="muted">—</span>;

  const avgText = summary.average !== null ? summary.average.toFixed(1) : "—";
  const ratingsWord = summary.count === 1 ? "rating" : "ratings";
  const segment = (kind: "weak" | "probable" | "strong", count: number) =>
    count > 0 ? (
      <span
        className={`consensus-bar__segment consensus-bar__segment--${kind}`}
        style={{ width: `${(count / total) * 100}%` }}
      />
    ) : null;

  return (
    <div className="ctd-strength">
      <div
        className="consensus-bar"
        role="img"
        aria-label={`Rating strength: ${weak} weak, ${probable} probable, ${strong} strong`}
      >
        {segment("weak", weak)}
        {segment("probable", probable)}
        {segment("strong", strong)}
      </div>
      <span className="ctd-strength-text">{`avg ${avgText} · ${summary.count} ${ratingsWord}`}</span>
    </div>
  );
}

type EvidenceState = Evidence[] | "loading" | "error";
type PendingAction = "accept" | "revise" | null;

export function ContestedPage() {
  const session = useActiveSession();
  const matterId = session.currentMatter.id;
  const canAdjudicate = session.role === "reviewer" || session.role === "admin";

  const [items, setItems] = useState<Assertion[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<Record<string, RatingSummary | null>>({});
  const [evidence, setEvidence] = useState<Record<string, EvidenceState>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [justification, setJustification] = useState("");
  const [revisionComment, setRevisionComment] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const aliveRef = useRef(true);
  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setLoadError(null);
    setSummaries({});
    setExpandedId(null);
    setPendingAction(null);
    setActionError(null);

    api.listAssertions(matterId, { status: "disputed" }).then(
      (list) => {
        if (cancelled) return;
        setItems(list.items);
        for (const assertion of list.items) {
          const revision = assertion.current_revision_number;
          if (revision === null) {
            setSummaries((prev) => ({ ...prev, [assertion.id]: null }));
            continue;
          }
          api.ratingSummary(assertion.id, revision).then(
            (summary) => {
              if (!cancelled) setSummaries((prev) => ({ ...prev, [assertion.id]: summary }));
            },
            () => {
              if (!cancelled) setSummaries((prev) => ({ ...prev, [assertion.id]: null }));
            },
          );
        }
      },
      (error: unknown) => {
        if (cancelled) return;
        setLoadError(
          error instanceof Error ? error.message : "Failed to load disputed assertions.",
        );
      },
    );

    return () => {
      cancelled = true;
    };
  }, [matterId, reloadKey]);

  function resetAction() {
    setPendingAction(null);
    setJustification("");
    setRevisionComment("");
    setActionError(null);
  }

  function toggleExpand(assertion: Assertion) {
    const next = expandedId === assertion.id ? null : assertion.id;
    setExpandedId(next);
    resetAction();
    if (next !== null && evidence[assertion.id] === undefined) {
      setEvidence((prev) => ({ ...prev, [assertion.id]: "loading" }));
      api.listEvidence(assertion.id).then(
        (list) => {
          if (aliveRef.current) setEvidence((prev) => ({ ...prev, [assertion.id]: list }));
        },
        () => {
          if (aliveRef.current) setEvidence((prev) => ({ ...prev, [assertion.id]: "error" }));
        },
      );
    }
  }

  async function runRuling(call: () => Promise<unknown>) {
    setActionBusy(true);
    setActionError(null);
    try {
      await call();
      if (!aliveRef.current) return;
      setActionBusy(false);
      setExpandedId(null);
      resetAction();
      // Evidence may have changed by the time the assertion is disputed
      // again — drop the cache alongside the list refresh.
      setEvidence({});
      setReloadKey((k) => k + 1);
    } catch (error) {
      if (!aliveRef.current) return;
      setActionBusy(false);
      setActionError(
        error instanceof ApiError && error.status === 403
          ? "Your role on this matter no longer permits review actions."
          : error instanceof Error
            ? error.message
            : "The action failed.",
      );
    }
  }

  function renderDrawer(assertion: Assertion) {
    const summary = summaries[assertion.id] ?? null;
    const distributionSummary = summary ?? {
      count: 0,
      average: null,
      median: null,
      distribution: {},
    };
    const evidenceState = evidence[assertion.id];

    return (
      <tr className="ctd-drawer-row">
        <td colSpan={6}>
          <div className="ctd-drawer">
            <div className="ctd-drawer__head">
              <span className="badge badge--disputed">Disputed</span>
              <p className="ctd-drawer__proposition">{assertion.proposition}</p>
            </div>

            <div className="ctd-drawer__grid">
              <section>
                <h3 className="ctd-section-title">Rating summary</h3>
                <div className="ctd-tiles">
                  <div className="ctd-tile">
                    <span className="ctd-tile__value">{summary ? summary.count : "—"}</span>
                    <span className="ctd-tile__label">Count</span>
                  </div>
                  <div className="ctd-tile">
                    <span className="ctd-tile__value">
                      {summary && summary.average !== null ? summary.average.toFixed(1) : "—"}
                    </span>
                    <span className="ctd-tile__label">Average</span>
                  </div>
                  <div className="ctd-tile">
                    <span className="ctd-tile__value">
                      {summary && summary.median !== null ? summary.median.toFixed(1) : "—"}
                    </span>
                    <span className="ctd-tile__label">Median</span>
                  </div>
                </div>
                <AssertionRatingDistribution
                  summary={distributionSummary}
                  modelConfidence={
                    assertion.origin === "model_suggested" ? assertion.confidence : null
                  }
                />
              </section>

              <section>
                <h3 className="ctd-section-title">Evidence</h3>
                {evidenceState === undefined || evidenceState === "loading" ? (
                  <p className="muted">Loading evidence…</p>
                ) : evidenceState === "error" ? (
                  <p className="muted">Could not load evidence for this assertion.</p>
                ) : evidenceState.length === 0 ? (
                  <p className="muted">No evidence spans linked.</p>
                ) : (
                  <ul className="ctd-evidence">
                    {evidenceState.map((item) => (
                      <li key={item.id} className="ctd-evidence__item">
                        <Icon name="description" size={16} />
                        <span className={evidenceRoleClass(item.evidence_role)}>
                          {item.evidence_role}
                        </span>
                        <span className="mono">{item.source_span_id}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            {canAdjudicate ? (
              <div className="ctd-adjudicate">
                {actionError && <div className="error-banner">{actionError}</div>}
                <div className="ctd-adjudicate__actions">
                  <button
                    type="button"
                    className="btn btn--primary"
                    disabled={actionBusy}
                    onClick={() => {
                      // The backend requires an acceptance justification
                      // whenever there is no supporting evidence, which
                      // covers both "unsupported" and "awaiting_evidence".
                      if (
                        assertion.evidence_status === "unsupported" ||
                        assertion.evidence_status === "awaiting_evidence"
                      ) {
                        setPendingAction("accept");
                        setActionError(null);
                      } else {
                        void runRuling(() => api.acceptAssertion(assertion.id));
                      }
                    }}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className="btn btn--danger-outline"
                    disabled={actionBusy}
                    onClick={() => void runRuling(() => api.rejectAssertion(assertion.id))}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={actionBusy}
                    onClick={() => {
                      setPendingAction("revise");
                      setActionError(null);
                    }}
                  >
                    Request revision
                  </button>
                </div>

                {pendingAction === "accept" && (
                  <div className="ctd-confirm">
                    <p className="ctd-confirm__note">
                      This assertion is unsupported by documentary evidence. Record a
                      justification to accept it anyway.
                    </p>
                    <label htmlFor={`ctd-justification-${assertion.id}`}>
                      Acceptance justification
                    </label>
                    <textarea
                      id={`ctd-justification-${assertion.id}`}
                      className="textarea"
                      value={justification}
                      onChange={(event) => setJustification(event.target.value)}
                    />
                    <div className="ctd-confirm__actions">
                      <button
                        type="button"
                        className="btn btn--primary"
                        disabled={actionBusy || justification.trim() === ""}
                        onClick={() =>
                          void runRuling(() =>
                            api.acceptAssertion(assertion.id, justification.trim()),
                          )
                        }
                      >
                        Confirm accept
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={actionBusy}
                        onClick={resetAction}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {pendingAction === "revise" && (
                  <div className="ctd-confirm">
                    <label htmlFor={`ctd-revision-${assertion.id}`}>
                      Comment explaining the requested revision
                    </label>
                    <textarea
                      id={`ctd-revision-${assertion.id}`}
                      className="textarea"
                      value={revisionComment}
                      onChange={(event) => setRevisionComment(event.target.value)}
                    />
                    <div className="ctd-confirm__actions">
                      <button
                        type="button"
                        className="btn btn--primary"
                        disabled={actionBusy || revisionComment.trim() === ""}
                        onClick={() =>
                          void runRuling(() =>
                            api.requestRevision(assertion.id, revisionComment.trim()),
                          )
                        }
                      >
                        Confirm request
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={actionBusy}
                        onClick={resetAction}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                <p className="ctd-footnote">Decisions are recorded in the assertion history.</p>
              </div>
            ) : (
              <p className="ctd-note">Reviewer role required to adjudicate.</p>
            )}
          </div>
        </td>
      </tr>
    );
  }

  return (
    <div className="ctd-page">
      <header className="page-header">
        <div>
          <h1 className="page-header__title">
            Contested
            {items !== null && <span className="page-header__count">{items.length}</span>}
          </h1>
          <p className="page-header__subtitle">
            Assertions a reviewer has marked disputed in {session.currentMatter.name} — awaiting
            adjudication.
          </p>
        </div>
      </header>

      {loadError ? (
        <div className="error-banner">
          {loadError}{" "}
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => setReloadKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      ) : items === null ? (
        <div className="loading">Loading disputed assertions…</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">No contested assertions</p>
          <p>Disputes land here for adjudication.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="table ctd-table">
              <thead>
                <tr>
                  <th>Assertion</th>
                  <th>Origin</th>
                  <th>Rating strength</th>
                  <th>Evidence</th>
                  <th>Disputed</th>
                  <th aria-label="Details" />
                </tr>
              </thead>
              <tbody>
                {items.map((assertion) => {
                  const expanded = expandedId === assertion.id;
                  const originChip = ORIGIN_CHIPS[assertion.origin];
                  const evidenceBadge = EVIDENCE_BADGES[assertion.evidence_status];
                  return (
                    <Fragment key={assertion.id}>
                      <tr className={expanded ? "ctd-row ctd-row--open" : "ctd-row"}>
                        <td className="ctd-prop-cell">
                          <Link to={`/assertions/${assertion.id}`} className="ctd-prop-link">
                            {assertion.proposition}
                          </Link>
                          <p className="ctd-type">
                            {assertion.assertion_type}
                            {assertion.jurisdiction ? ` · ${assertion.jurisdiction}` : ""}
                          </p>
                        </td>
                        <td>
                          <span className={originChip.className}>{originChip.label}</span>
                        </td>
                        <td>
                          <StrengthCell summary={summaries[assertion.id]} />
                        </td>
                        <td>
                          <span className={evidenceBadge.className}>{evidenceBadge.label}</span>
                        </td>
                        <td className="ctd-date">
                          {formatDate(assertion.reviewed_at ?? assertion.updated_at)}
                        </td>
                        <td className="ctd-toggle-cell">
                          <button
                            type="button"
                            className={expanded ? "ctd-toggle ctd-toggle--open" : "ctd-toggle"}
                            aria-expanded={expanded}
                            aria-label={expanded ? "Collapse row" : "Expand row"}
                            onClick={() => toggleExpand(assertion)}
                          >
                            <Icon name="chevron-right" size={18} />
                          </button>
                        </td>
                      </tr>
                      {expanded && renderDrawer(assertion)}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
