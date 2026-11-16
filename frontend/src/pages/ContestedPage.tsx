// ContestedPage — adjudication queue for status=disputed assertions.
//
// A reviewer marks an assertion disputed elsewhere (review queue / detail
// page); everything disputed in the current matter lands here for a final
// ruling. The three signals stay strictly separate per the platform spec:
// user strength ratings (1-5 aggregate), model confidence (only for
// AI-deduced assertions), and review status. Ratings never decide the
// outcome — the reviewer's adjudication does.
//
// The table lists the first CONTESTED_PAGE disputed assertions (in the
// order they were created) and grows with "Show more". Each row's rating
// aggregate comes with the list item (ratings_summary).

import { Fragment, useEffect, useRef, useState } from "react";

import "../styles/pages/contested.css";

import { ApiError, api } from "../api/client";
import { formatInstantDate } from "../api/datetime";
import { listWindow } from "../api/listWindow";
import type { Assertion, AssertionListItem, Evidence } from "../api/types";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";
import type { AssertionRatingDistributionSummary } from "../components/AssertionRatingDistribution";
import { SUPPORTING_EVIDENCE_ROLES } from "../constants/evidence";
import {
  isSystemDerived,
  SYSTEM_DERIVED_LABEL,
  SYSTEM_DERIVED_NO_EVIDENCE,
} from "../constants/pipeline";
import {
  REVIEW_EVIDENCE_REMOVED_MESSAGE,
  reviewConflictNotice,
  reviewTextProblem,
  reviewTextTooLongMessage,
} from "../constants/review";

/** Rows shown at first, and added by each "Show more". */
const CONTESTED_PAGE = 50;

/** Rating summaries a list item lacks are requested this many at a time. */
const SUMMARY_FETCH_BATCH = 30;

/** The aggregate of a revision nobody has rated (the list sends null). */
const UNRATED: AssertionRatingDistributionSummary = {
  count: 0,
  average: null,
  median: null,
  distribution: {},
};

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

/** fe-review-detail:5 (ui:4): a definition-linking pipeline row without
 * evidence, labelled as on the assertion page. */
const SYSTEM_DERIVED_BADGE = { className: "badge badge--neutral", label: SYSTEM_DERIVED_LABEL };

function evidenceRoleClass(role: string): string {
  if (SUPPORTING_EVIDENCE_ROLES.has(role)) return "badge badge--accepted";
  if (role === "contradicts") return "badge badge--rejected";
  return "badge badge--neutral";
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

/** Summaries are per revision: a revised row must not show the old ratings. */
function summaryKey(assertion: AssertionListItem): string {
  return `${assertion.id}@${assertion.current_revision_number}`;
}

/** Compact weak/probable/strong strength bar for a queue row. */
function StrengthCell({
  summary,
}: {
  summary: AssertionRatingDistributionSummary | null | undefined;
}) {
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

  // How many rows to list belongs to one matter; a switch starts over. The
  // reset is stored during render, so no request goes out with the
  // previous matter's size.
  const [windowState, setWindowState] = useState({ matterId, size: CONTESTED_PAGE });
  if (windowState.matterId !== matterId) setWindowState({ matterId, size: CONTESTED_PAGE });
  const windowSize = windowState.matterId === matterId ? windowState.size : CONTESTED_PAGE;
  // The matter the rows on screen belong to: a reload or "Show more" keeps
  // them (and an open drawer) on screen; another matter's are dropped.
  const shownMatterRef = useRef<string | null>(null);

  const [items, setItems] = useState<AssertionListItem[] | null>(null);
  // Every disputed assertion of the matter, also those not listed yet.
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Only for rows whose list item carries no aggregate, keyed by
  // id@revision. undefined: loading; null: the request failed.
  const [summaries, setSummaries] = useState<
    Record<string, AssertionRatingDistributionSummary | null>
  >({});
  const [evidence, setEvidence] = useState<Record<string, EvidenceState>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [justification, setJustification] = useState("");
  const [revisionComment, setRevisionComment] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // Page level, not in the drawer: the reload after a refused (409) ruling
  // collapses the drawer and clears `actionError`.
  const [rulingNotice, setRulingNotice] = useState<string | null>(null);

  const aliveRef = useRef(true);
  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);
  // The newest evidence request per assertion: an older answer is dropped.
  const evidenceRequests = useRef<Record<string, number>>({});
  // One ruling at a time: also stops a second click that lands before the
  // disabled buttons are rendered.
  const rulingRef = useRef(false);

  function resetAction() {
    setPendingAction(null);
    setJustification("");
    setRevisionComment("");
    setActionError(null);
  }

  // A matter switch drops the previous matter's drawer and notice.
  useEffect(() => {
    setRulingNotice(null);
    setExpandedId(null);
    resetAction();
    setEvidence({});
  }, [matterId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    if (shownMatterRef.current !== matterId) {
      shownMatterRef.current = null;
      setItems(null);
      setSummaries({});
    }

    listWindow(matterId, { status: "disputed" }, windowSize).then(
      async (list) => {
        if (cancelled) return;
        shownMatterRef.current = matterId;
        setItems(list.items);
        setTotal(list.total);
        setLoading(false);

        // A list item without an aggregate gets its revision summary
        // requested, a batch at a time; the final map drops rows that left.
        const targets = list.items.filter(
          (a) => a.current_revision_number !== null && !("ratings_summary" in a),
        );
        const fresh: Record<string, AssertionRatingDistributionSummary | null> = {};
        for (let start = 0; start < targets.length; start += SUMMARY_FETCH_BATCH) {
          const batch = targets.slice(start, start + SUMMARY_FETCH_BATCH);
          const results = await Promise.all(
            batch.map((a) =>
              api.ratingSummary(a.id, a.current_revision_number as number).then(
                (summary) => [summaryKey(a), summary] as const,
                () => [summaryKey(a), null] as const,
              ),
            ),
          );
          if (cancelled) return;
          const landed = Object.fromEntries(results);
          Object.assign(fresh, landed);
          setSummaries((prev) => ({ ...prev, ...landed }));
        }
        setSummaries(fresh);
      },
      (error: unknown) => {
        if (cancelled) return;
        shownMatterRef.current = null;
        setItems(null);
        setLoading(false);
        setLoadError(
          error instanceof Error ? error.message : "Failed to load disputed assertions.",
        );
      },
    );

    return () => {
      cancelled = true;
    };
  }, [matterId, windowSize, reloadKey]);

  /** The row's aggregate: a requested summary, else the list item's own;
   * undefined while loading, null when it could not be loaded. */
  function summaryOf(assertion: AssertionListItem): AssertionRatingDistributionSummary | null | undefined {
    if (assertion.current_revision_number === null) return null;
    const requested = summaries[summaryKey(assertion)];
    if (requested) return requested;
    if ("ratings_summary" in assertion) return assertion.ratings_summary ?? UNRATED;
    return requested;
  }

  function loadEvidence(id: string) {
    const request = (evidenceRequests.current[id] ?? 0) + 1;
    evidenceRequests.current[id] = request;
    const current = () => aliveRef.current && evidenceRequests.current[id] === request;
    setEvidence((prev) => ({ ...prev, [id]: "loading" }));
    api.listEvidence(id).then(
      (list) => {
        if (current()) setEvidence((prev) => ({ ...prev, [id]: list }));
      },
      () => {
        if (current()) setEvidence((prev) => ({ ...prev, [id]: "error" }));
      },
    );
  }

  function toggleExpand(assertion: AssertionListItem) {
    const next = expandedId === assertion.id ? null : assertion.id;
    setExpandedId(next);
    resetAction();
    if (next !== null && evidence[assertion.id] === undefined) loadEvidence(assertion.id);
  }

  /**
   * Records one ruling. `acceptWithoutJustificationOf` names the assertion of
   * an acceptance sent without a justification (its row showed supporting
   * evidence).
   */
  async function runRuling(
    call: () => Promise<unknown>,
    { acceptWithoutJustificationOf }: { acceptWithoutJustificationOf?: string } = {},
  ) {
    if (rulingRef.current) return;
    rulingRef.current = true;
    setActionBusy(true);
    setActionError(null);
    setRulingNotice(null);
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
      if (error instanceof ApiError && error.status === 409) {
        // The drawer was stale (edited, withdrawn or decided meanwhile):
        // nothing was recorded. Say so above the table, close the drawer
        // and reload the queue as it now is.
        setRulingNotice(reviewConflictNotice(error.message));
        setExpandedId(null);
        resetAction();
        setEvidence({});
        setReloadKey((k) => k + 1);
        return;
      }
      if (
        error instanceof ApiError &&
        error.status === 422 &&
        acceptWithoutJustificationOf !== undefined
      ) {
        // fe-review-detail:2: the drawer still showed supporting evidence
        // that was removed meanwhile (that changes neither the revision nor
        // updated_at). Nothing was recorded: say so above the table, re-read
        // the row and its evidence with the drawer kept open, and ask for
        // the justification. `loading` is set in this render, so the drawer
        // stays disabled until the reloaded row is shown.
        setRulingNotice(REVIEW_EVIDENCE_REMOVED_MESSAGE);
        setActionError(null);
        setPendingAction("accept");
        loadEvidence(acceptWithoutJustificationOf);
        setLoading(true);
        setReloadKey((k) => k + 1);
        return;
      }
      setActionError(
        error instanceof ApiError && error.status === 403
          ? "Your role on this matter no longer permits review actions."
          : error instanceof Error
            ? error.message
            : "The action failed.",
      );
    } finally {
      rulingRef.current = false;
    }
  }

  function renderDrawer(assertion: AssertionListItem) {
    const summary = summaryOf(assertion) ?? null;
    const distributionSummary = summary ?? UNRATED;
    // No ruling while one is recorded or the queue reloads after one: the
    // row may still show a status that has just changed.
    const busy = actionBusy || loading;
    const evidenceState = evidence[assertion.id];
    // Same rules as the API: trimmed text, required, at most 100,000 characters.
    const justificationProblem = reviewTextProblem(justification);
    const revisionCommentProblem = reviewTextProblem(revisionComment);

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
                  <p className="muted">
                    {assertion.origin === "system_generated"
                      ? SYSTEM_DERIVED_NO_EVIDENCE
                      : "No evidence spans linked."}
                  </p>
                ) : (
                  <ul className="ctd-evidence">
                    {evidenceState.map((item) => (
                      <li key={item.id} className="ctd-evidence__item">
                        <Icon name="description" size={16} />
                        <div className="ctd-evidence__body">
                          <div className="ctd-evidence__meta">
                            <span className={evidenceRoleClass(item.evidence_role)}>
                              {item.evidence_role.replace(/_/g, " ")}
                            </span>
                            {item.document_title && (
                              <span className="ctd-evidence__source">{item.document_title}</span>
                            )}
                          </div>
                          {item.quote_text ? (
                            <blockquote className="ctd-evidence__quote">{item.quote_text}</blockquote>
                          ) : (
                            // The API resolves a span only within this matter;
                            // its id means nothing to a reader (XREQ-46).
                            <p className="ctd-evidence__missing">
                              Source span unavailable: the quoted passage could not be found in
                              this matter.
                            </p>
                          )}
                        </div>
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
                    disabled={busy}
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
                        void runRuling(
                          () =>
                            api.acceptAssertion(
                              assertion.id,
                              undefined,
                              assertion.current_revision_number,
                            ),
                          { acceptWithoutJustificationOf: assertion.id },
                        );
                      }
                    }}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className="btn btn--danger-outline"
                    disabled={busy}
                    onClick={() =>
                      void runRuling(() =>
                        api.rejectAssertion(assertion.id, assertion.current_revision_number),
                      )
                    }
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={busy}
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
                    {justificationProblem === "too_long" && (
                      <p className="ctd-confirm__error" role="alert">
                        {reviewTextTooLongMessage(justification)}
                      </p>
                    )}
                    <div className="ctd-confirm__actions">
                      <button
                        type="button"
                        className="btn btn--primary"
                        disabled={busy || justificationProblem !== null}
                        onClick={() =>
                          void runRuling(() =>
                            api.acceptAssertion(
                              assertion.id,
                              justification.trim(),
                              assertion.current_revision_number,
                            ),
                          )
                        }
                      >
                        Confirm accept
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={busy}
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
                    {revisionCommentProblem === "too_long" && (
                      <p className="ctd-confirm__error" role="alert">
                        {reviewTextTooLongMessage(revisionComment)}
                      </p>
                    )}
                    <div className="ctd-confirm__actions">
                      <button
                        type="button"
                        className="btn btn--primary"
                        disabled={busy || revisionCommentProblem !== null}
                        onClick={() =>
                          void runRuling(() =>
                            api.requestRevision(
                              assertion.id,
                              revisionComment.trim(),
                              assertion.current_revision_number,
                            ),
                          )
                        }
                      >
                        Confirm request
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        disabled={busy}
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
            {items !== null && <span className="page-header__count">{formatCount(total)}</span>}
          </h1>
          <p className="page-header__subtitle">
            Assertions a reviewer has marked disputed in {session.currentMatter.name} — awaiting
            adjudication.
          </p>
        </div>
      </header>

      {rulingNotice && (
        <div className="error-banner" role="alert">
          {rulingNotice}
        </div>
      )}

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
                  const evidenceBadge = isSystemDerived(assertion)
                    ? SYSTEM_DERIVED_BADGE
                    : EVIDENCE_BADGES[assertion.evidence_status];
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
                          <StrengthCell summary={summaryOf(assertion)} />
                        </td>
                        <td>
                          <span className={evidenceBadge.className}>{evidenceBadge.label}</span>
                        </td>
                        <td className="ctd-date">
                          {formatInstantDate(assertion.reviewed_at ?? assertion.updated_at, "en-US")}
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
          {total > items.length && (
            <div className="ctd-more">
              <span>
                Showing {formatCount(items.length)} of {formatCount(total)}
              </span>
              <button
                type="button"
                className="btn btn--sm btn--secondary"
                disabled={loading}
                onClick={() => setWindowState({ matterId, size: windowSize + CONTESTED_PAGE })}
              >
                {loading ? "Loading…" : "Show more"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
