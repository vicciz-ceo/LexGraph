// Review Queue — the reviewer inbox. Merges the two Stitch queue designs:
// queue_1's layout (header + pending chip + filter pills + guidelines rail)
// with queue_2's richer card internals, adapted to the real LexGraph API:
// no votes/quorums — user strength ratings, model confidence, and review
// status stay three separate indicators.
//
// The queue shows the newest QUEUE_PAGE cards of the selected statuses and
// grows by QUEUE_PAGE with "Show more", so agent bulk authoring cannot make
// it load every open assertion at once. Each card's rating aggregate comes
// with the list item (ratings_summary); a card's revision summary is only
// requested when the item has none, or when its current revision is unrated
// while earlier revisions may hold ratings (spec §10: the reviewer is told).

import "../styles/pages/review-queue.css";

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api/client";
import { formatInstantDate, parseApiInstant } from "../api/datetime";
import { listWindow } from "../api/listWindow";
import type {
  AssertionListItem,
  AssertionOrigin,
  AssertionStatus,
  EvidenceStatus,
  RatingSummary,
} from "../api/types";
import type { IconName } from "../app/icons";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { useRefreshOnReturn } from "../app/useRefreshOnReturn";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";
import type { AssertionRatingDistributionSummary } from "../components/AssertionRatingDistribution";
import { AssertionReviewPanel } from "../components/AssertionReviewPanel";
import type { ReviewDecisionOutcome } from "../components/AssertionReviewPanel";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";
import { isSystemDerived, SYSTEM_DERIVED_LABEL } from "../constants/pipeline";
import { REVIEW_EVIDENCE_REMOVED_MESSAGE, reviewConflictNotice } from "../constants/review";

/** Cards shown at first, and added by each "Show more". */
const QUEUE_PAGE = 50;

/**
 * Revision summaries are requested newest card first, in sequential batches
 * of this size, so a large queue never has more requests in flight.
 */
const SUMMARY_FETCH_BATCH = 30;

/** The aggregate of a revision nobody has rated (the list sends null). */
const UNRATED: AssertionRatingDistributionSummary = {
  count: 0,
  average: null,
  median: null,
  distribution: {},
};

/** Summaries are per revision: a revised card must not show the old ratings. */
function summaryKey(assertion: AssertionListItem): string {
  return `${assertion.id}@${assertion.current_revision_number}`;
}

/**
 * Whether the card's revision summary must be requested: the list item
 * carries no aggregate, or its current revision is unrated and only the
 * revision summary says whether earlier revisions were rated
 * (prior_revision_rating_count).
 */
function needsSummaryRequest(assertion: AssertionListItem): boolean {
  const revision = assertion.current_revision_number;
  if (revision === null) return false;
  if (!("ratings_summary" in assertion)) return true;
  return (assertion.ratings_summary?.count ?? 0) === 0 && revision > 1;
}

function newestFirst(a: AssertionListItem, b: AssertionListItem): number {
  return (
    (parseApiInstant(b.created_at)?.getTime() ?? 0) - (parseApiInstant(a.created_at)?.getTime() ?? 0)
  );
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

type StatusFilterKey = "proposed" | "revision_requested" | "open";
type OriginFilterKey = "all" | AssertionOrigin;

const STATUS_FILTERS: {
  key: StatusFilterKey;
  label: string;
  statuses: AssertionStatus[];
}[] = [
  { key: "proposed", label: "Proposed", statuses: ["proposed"] },
  {
    key: "revision_requested",
    label: "Revision requested",
    statuses: ["revision_requested"],
  },
  {
    key: "open",
    label: "All open",
    statuses: ["proposed", "revision_requested", "disputed"],
  },
];

const ORIGIN_FILTERS: { key: OriginFilterKey; label: string }[] = [
  { key: "all", label: "All origins" },
  { key: "model_suggested", label: "AI-deduced" },
  { key: "user_suggested", label: "Colleague" },
];

const ORIGIN_META: Record<
  AssertionOrigin,
  { className: string; label: string; icon: IconName }
> = {
  model_suggested: { className: "chip chip--model", label: "AI-deduced", icon: "robot" },
  user_suggested: { className: "chip chip--user", label: "Colleague", icon: "person" },
  system_generated: { className: "chip chip--system", label: "System", icon: "settings" },
};

const STATUS_LABELS: Record<AssertionStatus, string> = {
  draft: "Draft",
  proposed: "Proposed",
  revision_requested: "Revision requested",
  accepted: "Accepted",
  rejected: "Rejected",
  disputed: "Disputed",
  superseded: "Superseded",
  withdrawn: "Withdrawn",
};

const EVIDENCE_LABELS: Record<EvidenceStatus, string> = {
  evidenced: "Evidenced",
  unsupported: "Unsupported evidence",
  awaiting_evidence: "Awaiting evidence",
};

const STANDING_GRADES = ["weak", "probable", "strong"];

const STRENGTH_SCALE: { value: number; label: string; hint: string }[] = [
  { value: 1, label: "Very weak", hint: "Contradicted or barely supported." },
  { value: 2, label: "Weak", hint: "Thin support; significant doubts remain." },
  { value: 3, label: "Plausible or mixed", hint: "Reasonable but contestable." },
  { value: 4, label: "Strong", hint: "Well supported by the evidence spans." },
  { value: 5, label: "Very strong", hint: "Directly established by the record." },
];

export function ReviewQueuePage() {
  const session = useActiveSession();
  const matterId = session.currentMatter.id;
  const canReview = session.role === "reviewer" || session.role === "admin";

  const [statusKey, setStatusKey] = useState<StatusFilterKey>("proposed");
  const [originKey, setOriginKey] = useState<OriginFilterKey>("all");
  const [jurisdiction, setJurisdiction] = useState("");

  // How many cards to show belongs to one result set (matter + filters):
  // any change starts over at QUEUE_PAGE. The reset is stored during render,
  // so no request goes out with the previous result set's size.
  const resultKey = `${matterId}|${statusKey}|${originKey}|${jurisdiction}`;
  const [windowState, setWindowState] = useState({ resultKey, size: QUEUE_PAGE });
  if (windowState.resultKey !== resultKey) setWindowState({ resultKey, size: QUEUE_PAGE });
  const windowSize = windowState.resultKey === resultKey ? windowState.size : QUEUE_PAGE;
  // The result set the cards on screen belong to: reloads and "Show more"
  // keep them (and any open decision form) mounted; a new one clears them.
  const shownKeyRef = useRef<string | null>(null);

  const [items, setItems] = useState<AssertionListItem[] | null>(null);
  // Every card of the selected statuses, also those not shown yet.
  const [queueTotal, setQueueTotal] = useState(0);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  // Keyed by summaryKey(). undefined: still loading; null: the request failed.
  const [summaries, setSummaries] = useState<Record<string, RatingSummary | null>>({});
  // null until the roster has loaded (or when it could not be loaded).
  const [memberNames, setMemberNames] = useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  // One decision at a time across the queue; the ref also stops a second
  // activation that lands before the disabled buttons are rendered.
  const [deciding, setDeciding] = useState(false);
  const decidingRef = useRef(false);

  // The page is not remounted when the matter changes: drop what belongs to
  // the previous matter (its pending count, a notice about its assertion).
  useEffect(() => {
    setPendingCount(null);
    setActionError(null);
  }, [matterId]);

  // Resolve author_user_id → display_name once per matter.
  useEffect(() => {
    let cancelled = false;
    setMemberNames(null);
    api
      .listMatterMembers(matterId)
      .then((res) => {
        if (cancelled) return;
        const names: Record<string, string> = {};
        for (const member of res) names[member.user.id] = member.user.display_name;
        setMemberNames(names);
      })
      .catch(() => {
        // Non-fatal: authors get a neutral label, never their user id.
      });
    return () => {
      cancelled = true;
    };
  }, [matterId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    if (shownKeyRef.current !== resultKey) {
      shownKeyRef.current = null;
      setItems(null);
    }

    const filter = STATUS_FILTERS.find((f) => f.key === statusKey) ?? STATUS_FILTERS[0];
    const originParams = originKey === "all" ? {} : { origin: originKey };
    const jurisdictionParams = jurisdiction ? { jurisdiction } : {};
    // The newest `windowSize` of each status: together they hold the newest
    // `windowSize` of the merged queue.
    const listPromises = filter.statuses.map((status) =>
      listWindow(
        matterId,
        { status, ...originParams, ...jurisdictionParams, sort: "-created_at" },
        windowSize,
      ),
    );
    // The pending chip always reflects the full proposed inbox regardless
    // of the active pills; only its total is needed.
    const pendingPromise = api.listAssertions(matterId, {
      status: "proposed",
      ...jurisdictionParams,
      limit: 1,
    });

    Promise.all([pendingPromise, ...listPromises])
      .then(async ([pending, ...lists]) => {
        if (cancelled) return;
        setPendingCount(pending.total);
        const merged = lists
          .flatMap((list) => list.items)
          .sort(newestFirst)
          .slice(0, windowSize);
        shownKeyRef.current = resultKey;
        setItems(merged);
        setQueueTotal(lists.reduce((sum, list) => sum + list.total, 0));
        setLoading(false);

        // Each batch is merged as it lands, so summaries already known (same
        // assertion, same revision) stay on screen through a reload; the
        // final map drops cards that left.
        const targets = merged.filter(needsSummaryRequest);
        const fresh: Record<string, RatingSummary | null> = {};
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
          const landed: Record<string, RatingSummary | null> = Object.fromEntries(results);
          Object.assign(fresh, landed);
          setSummaries((prev) => ({ ...prev, ...landed }));
        }
        setSummaries(fresh);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoading(false);
        shownKeyRef.current = null;
        setItems(null);
        // The count can no longer be vouched for (and may be another
        // matter's or another jurisdiction's).
        setPendingCount(null);
        setLoadError(err instanceof Error ? err.message : "Unexpected error.");
      });

    return () => {
      cancelled = true;
    };
  }, [matterId, statusKey, originKey, jurisdiction, resultKey, windowSize, reloadKey]);

  /**
   * Re-reads the queue after a decision. `loading` is set in the same render
   * that ends the decision, so no card is decidable again (`busy`) before the
   * reloaded cards are shown.
   */
  function reloadAfterDecision() {
    setLoading(true);
    setReloadKey((key) => key + 1);
  }

  // The queue is read again when the reviewer comes back to it, so proposals
  // submitted meanwhile show up: on a click of its own nav link (which also
  // clears the notice of an earlier decision, as opening the page does) and
  // on returning to this tab or window. The cards on screen stay mounted, with
  // any decision form and its text. Not during a decision, whose own re-read
  // follows, and a return while a read is on its way adds none (one return
  // can bring both a focus and a visibilitychange event).
  const loadingRef = useRef(loading);
  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);
  useRefreshOnReturn((cause) => {
    if (decidingRef.current || (cause === "return" && loadingRef.current)) return;
    if (cause === "link") setActionError(null);
    loadingRef.current = true;
    reloadAfterDecision();
  });

  /** Records one decision; resolves to whether it was recorded. */
  async function runReviewAction(
    action: () => Promise<unknown>,
    { acceptWithoutJustification = false }: { acceptWithoutJustification?: boolean } = {},
  ): Promise<ReviewDecisionOutcome> {
    if (decidingRef.current) return false;
    decidingRef.current = true;
    setDeciding(true);
    setActionError(null);
    try {
      await action();
      reloadAfterDecision();
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // The card was stale (edited, withdrawn or decided meanwhile):
        // nothing was recorded. Say so and show the queue as it now is.
        setActionError(reviewConflictNotice(err.message));
        reloadAfterDecision();
      } else if (err instanceof ApiError && err.status === 422 && acceptWithoutJustification) {
        // fe-review-detail:2: the card still showed supporting evidence that
        // was removed meanwhile (that changes neither the revision nor
        // updated_at). Nothing was recorded: say so, show the card as it now
        // is, and let its panel ask for the justification.
        setActionError(REVIEW_EVIDENCE_REMOVED_MESSAGE);
        reloadAfterDecision();
        return "needs-justification";
      } else if (err instanceof ApiError && err.status === 403) {
        setActionError(
          "Your role on this matter does not permit review decisions. Ask a matter admin for the reviewer role.",
        );
      } else {
        setActionError(err instanceof Error ? err.message : "Review action failed.");
      }
      return false;
    } finally {
      decidingRef.current = false;
      setDeciding(false);
    }
  }

  // A user id is never a person's label (ui:0): someone no longer on the
  // roster is a former member; without a roster only a neutral label fits.
  function authorName(userId: string): string {
    if (userId === session.user.id) return session.user.display_name;
    if (memberNames === null) return "Team member";
    return memberNames[userId] ?? "Former member";
  }

  const showMore = () => setWindowState({ resultKey, size: windowSize + QUEUE_PAGE });

  return (
    <div className="rq">
      <header className="page-header">
        <div>
          <h1 className="page-header__title">
            Review Queue
            {pendingCount !== null && (
              <span className="page-header__count">{pendingCount} pending</span>
            )}
          </h1>
          <p className="page-header__subtitle">
            Proposed assertions awaiting review in {session.currentMatter.name}.
            Strength ratings inform reviewers — acceptance is a separate reviewer
            decision.
          </p>
        </div>
      </header>

      <div className="filter-bar rq-filters">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.key}
            type="button"
            className={
              statusKey === filter.key
                ? "filter-bar__pill filter-bar__pill--active"
                : "filter-bar__pill"
            }
            aria-pressed={statusKey === filter.key}
            onClick={() => setStatusKey(filter.key)}
          >
            {filter.label}
          </button>
        ))}
        <span className="rq-filters__divider" aria-hidden="true" />
        {ORIGIN_FILTERS.map((filter) => (
          <button
            key={filter.key}
            type="button"
            className={
              originKey === filter.key
                ? "filter-bar__pill filter-bar__pill--active"
                : "filter-bar__pill"
            }
            aria-pressed={originKey === filter.key}
            onClick={() => setOriginKey(filter.key)}
          >
            {filter.label}
          </button>
        ))}
        <span className="rq-filters__divider" aria-hidden="true" />
        <label className="rq-filters__jurisdiction">
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
      </div>

      <div className="rq-layout">
        <div className="rq-main">
          {loadError && (
            <div className="error-banner" role="alert">
              Couldn&apos;t load the review queue. {loadError}{" "}
              <button
                type="button"
                className="btn btn--sm btn--secondary"
                onClick={() => setReloadKey((key) => key + 1)}
              >
                Retry
              </button>
            </div>
          )}
          {actionError && (
            <div className="error-banner" role="alert">
              {actionError}
            </div>
          )}

          {loadError ? null : items === null || (loading && items.length === 0) ? (
            loading && <div className="loading">Loading review queue…</div>
          ) : items.length > 0 ? (
            <>
              <div className="rq-list" aria-busy={loading}>
                {items.map((assertion) => {
                  const origin = ORIGIN_META[assertion.origin];
                  // A requested revision summary (when there is one) is the
                  // fuller record; otherwise the list item's own aggregate.
                  const requested = summaries[summaryKey(assertion)];
                  const embedded =
                    "ratings_summary" in assertion
                      ? (assertion.ratings_summary ?? UNRATED)
                      : undefined;
                  const summary = requested ?? embedded;
                  // Spec §10: an unrated revision whose earlier revisions
                  // were rated says so to the reviewer (ui:12).
                  const hasRatingsOnPriorRevision =
                    requested != null &&
                    requested.count === 0 &&
                    (requested.prior_revision_rating_count ?? 0) > 0;
                  const showStanding =
                    assertion.status === "proposed" &&
                    STANDING_GRADES.includes(assertion.standing);
                  // fe-review-detail:5 (ui:4): a definition-linking pipeline
                  // row is shown as on the assertion page: the user the run
                  // is attributed to did not suggest it, and without evidence
                  // it is "System-derived", not "Awaiting evidence".
                  const byline =
                    assertion.origin === "system_generated"
                      ? `Generated by the definition-linking pipeline · run attributed to ${authorName(assertion.author_user_id)}`
                      : `Suggested by ${authorName(assertion.author_user_id)}`;
                  const systemDerived = isSystemDerived(assertion);
                  return (
                    <article key={assertion.id} className="card rq-card">
                      <div className="card__body rq-card__body">
                        <div className="rq-card__chips">
                          <span className={origin.className}>
                            <Icon name={origin.icon} size={13} />
                            {origin.label}
                          </span>
                          <span className={`badge badge--${assertion.status}`}>
                            {STATUS_LABELS[assertion.status]}
                          </span>
                          {showStanding && (
                            <span className={`badge badge--${assertion.standing}`}>
                              {assertion.standing} standing
                            </span>
                          )}
                          <span
                            className={`chip rq-evidence rq-evidence--${
                              systemDerived ? "system" : assertion.evidence_status
                            }`}
                          >
                            {systemDerived
                              ? SYSTEM_DERIVED_LABEL
                              : EVIDENCE_LABELS[assertion.evidence_status]}
                          </span>
                          {assertion.origin === "model_suggested" &&
                            assertion.confidence !== null && (
                              <span className="chip rq-confidence">
                                Model confidence {Math.round(assertion.confidence * 100)}%
                              </span>
                            )}
                          <span className="chip chip--tag">{assertion.assertion_type}</span>
                          {assertion.jurisdiction && (
                            <span className="chip chip--tag">{assertion.jurisdiction}</span>
                          )}
                        </div>

                        <h2 className="rq-card__proposition">
                          <Link to={`/assertions/${assertion.id}`}>
                            {assertion.proposition}
                          </Link>
                        </h2>

                        <p className="rq-card__meta muted">
                          {byline} · {formatInstantDate(assertion.created_at)}
                        </p>

                        <div className="rq-card__summary">
                          {assertion.current_revision_number === null ? (
                            <p className="rq-card__summary-note muted">No revision to rate yet.</p>
                          ) : summary ? (
                            <AssertionRatingDistribution
                              summary={{
                                count: summary.count,
                                average: summary.average,
                                median: summary.median,
                                distribution: summary.distribution,
                              }}
                              modelConfidence={null}
                            />
                          ) : (
                            <p className="rq-card__summary-note muted">
                              {requested === null
                                ? "Ratings unavailable. Open the assertion to view them."
                                : "Loading ratings…"}
                            </p>
                          )}
                        </div>

                        {canReview ? (
                          <div className="rq-card__review">
                            <AssertionReviewPanel
                              assertion={{
                                id: assertion.id,
                                status: assertion.status,
                                // The backend requires an acceptance justification
                                // whenever there is no supporting evidence, which
                                // covers both "unsupported" and "awaiting_evidence".
                                // The panel only gates on "unsupported", so map the
                                // latter onto it here (the card's evidence chip
                                // shows the real evidence_status, or System-derived
                                // for a pipeline row without evidence).
                                evidenceStatus:
                                  assertion.evidence_status === "awaiting_evidence"
                                    ? "unsupported"
                                    : assertion.evidence_status,
                                currentRevisionNumber:
                                  assertion.current_revision_number ?? undefined,
                              }}
                              // Every decision names the revision this card shows,
                              // so the API refuses it (409) if the text changed.
                              onAccept={(payload) => {
                                const justification =
                                  payload?.justification?.trim() || undefined;
                                return runReviewAction(
                                  () =>
                                    api.acceptAssertion(
                                      assertion.id,
                                      justification,
                                      assertion.current_revision_number,
                                    ),
                                  { acceptWithoutJustification: justification === undefined },
                                );
                              }}
                              onReject={() =>
                                runReviewAction(() =>
                                  api.rejectAssertion(
                                    assertion.id,
                                    assertion.current_revision_number,
                                  ),
                                )
                              }
                              onDispute={() =>
                                runReviewAction(() =>
                                  api.disputeAssertion(
                                    assertion.id,
                                    assertion.current_revision_number,
                                  ),
                                )
                              }
                              onRequestRevision={({ comment }) =>
                                runReviewAction(() =>
                                  api.requestRevision(
                                    assertion.id,
                                    comment,
                                    assertion.current_revision_number,
                                  ),
                                )
                              }
                              hasRatingsOnPriorRevision={hasRatingsOnPriorRevision}
                              // Also while the queue reloads: a card may show a
                              // status that a decision has just changed.
                              busy={deciding || loading}
                            />
                          </div>
                        ) : (
                          <p className="rq-card__readonly muted">
                            Reviewer role required to decide.
                          </p>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
              {queueTotal > items.length && (
                <div className="rq-more">
                  <span>
                    Showing the newest {formatCount(items.length)} of {formatCount(queueTotal)}
                  </span>
                  <button
                    type="button"
                    className="btn btn--sm btn--secondary"
                    disabled={loading}
                    onClick={showMore}
                  >
                    {loading ? "Loading…" : "Show more"}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p className="empty-state__title">Queue clear</p>
              <p>No assertions match this filter — nothing awaiting review right now.</p>
            </div>
          )}
        </div>

        <aside className="rq-rail" aria-label="Review guidance">
          <section className="card">
            <h2 className="card__header">Review guidelines</h2>
            <div className="card__body">
              <p className="rq-rail__heading">Acceptance criteria</p>
              <ul className="rq-rail__list">
                <li>Factually grounded in evidence spans from matter documents.</li>
                <li>Scoped to this matter — no general legal commentary.</li>
                <li>Free of subjective phrasing.</li>
                <li>
                  Accepting an assertion without supporting evidence requires a
                  recorded justification.
                </li>
              </ul>
            </div>
          </section>

          <section className="card">
            <h2 className="card__header">Strength rating scale</h2>
            <div className="card__body">
              <ol className="rq-rail__scale">
                {STRENGTH_SCALE.map((step) => (
                  <li key={step.value}>
                    <span className="rq-rail__scale-num" aria-hidden="true">
                      {step.value}
                    </span>
                    <span>
                      <strong>{step.label}</strong> — {step.hint}
                    </span>
                  </li>
                ))}
              </ol>
              <p className="rq-rail__note">
                Ratings inform reviewers — they never accept or reject an assertion.
              </p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
