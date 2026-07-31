// Review Queue — the reviewer inbox. Merges the two Stitch queue designs:
// queue_1's layout (header + pending chip + filter pills + guidelines rail)
// with queue_2's richer card internals, adapted to the real LexGraph API:
// no votes/quorums — user strength ratings, model confidence, and review
// status stay three separate indicators.

import "../styles/pages/review-queue.css";

import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import type {
  Assertion,
  AssertionOrigin,
  AssertionStatus,
  RatingSummary,
} from "../api/types";
import type { IconName } from "../app/icons";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";
import { AssertionReviewPanel } from "../components/AssertionReviewPanel";

/** Keep per-card summary fetches bounded on large queues. */
const SUMMARY_FETCH_CAP = 30;

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

const EVIDENCE_LABELS: Record<Assertion["evidence_status"], string> = {
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

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ReviewQueuePage() {
  const session = useActiveSession();
  const matterId = session.currentMatter.id;
  const canReview = session.role === "reviewer" || session.role === "admin";

  const [statusKey, setStatusKey] = useState<StatusFilterKey>("proposed");
  const [originKey, setOriginKey] = useState<OriginFilterKey>("all");

  const [items, setItems] = useState<Assertion[] | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const [summaries, setSummaries] = useState<Record<string, RatingSummary>>({});
  const [memberNames, setMemberNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Resolve author_user_id → display_name once per matter.
  useEffect(() => {
    let cancelled = false;
    api
      .listMatterMembers(matterId)
      .then((res) => {
        if (cancelled) return;
        const names: Record<string, string> = {};
        for (const member of res) names[member.user.id] = member.user.display_name;
        setMemberNames(names);
      })
      .catch(() => {
        // Non-fatal: authors fall back to raw user ids.
      });
    return () => {
      cancelled = true;
    };
  }, [matterId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    const filter = STATUS_FILTERS.find((f) => f.key === statusKey) ?? STATUS_FILTERS[0];
    const originParams = originKey === "all" ? {} : { origin: originKey };
    const listPromises = filter.statuses.map((status) =>
      api.listAssertions(matterId, { status, ...originParams }),
    );
    // The pending chip always reflects the full proposed inbox regardless
    // of the active pills.
    const pendingPromise = api.listAssertions(matterId, { status: "proposed" });

    Promise.all([pendingPromise, ...listPromises])
      .then(async ([pending, ...lists]) => {
        if (cancelled) return;
        setPendingCount(pending.total);
        const merged = lists
          .flatMap((list) => list.items)
          .sort((a, b) => b.created_at.localeCompare(a.created_at));
        setItems(merged);
        setLoading(false);

        const targets = merged
          .slice(0, SUMMARY_FETCH_CAP)
          .filter((a) => a.current_revision_number !== null);
        const results = await Promise.all(
          targets.map((a) =>
            api.ratingSummary(a.id, a.current_revision_number as number).then(
              (summary) => [a.id, summary] as const,
              () => null,
            ),
          ),
        );
        if (cancelled) return;
        const next: Record<string, RatingSummary> = {};
        for (const entry of results) if (entry) next[entry[0]] = entry[1];
        setSummaries(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoading(false);
        setItems(null);
        setLoadError(err instanceof Error ? err.message : "Unexpected error.");
      });

    return () => {
      cancelled = true;
    };
  }, [matterId, statusKey, originKey, reloadKey]);

  async function runReviewAction(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      setReloadKey((key) => key + 1);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setActionError(
          "Your role on this matter does not permit review decisions. Ask a matter admin for the reviewer role.",
        );
      } else {
        setActionError(err instanceof Error ? err.message : "Review action failed.");
      }
    }
  }

  function authorName(userId: string): string {
    return memberNames[userId] ?? userId;
  }

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
      </div>

      <div className="rq-layout">
        <div className="rq-main">
          {loadError && (
            <div className="error-banner" role="alert">
              Couldn&apos;t load the review queue. {loadError}
            </div>
          )}
          {actionError && (
            <div className="error-banner" role="alert">
              {actionError}
            </div>
          )}

          {loading ? (
            <div className="loading">Loading review queue…</div>
          ) : items && items.length > 0 ? (
            <div className="rq-list">
              {items.map((assertion) => {
                const origin = ORIGIN_META[assertion.origin];
                const summary = summaries[assertion.id];
                const showStanding =
                  assertion.status === "proposed" &&
                  STANDING_GRADES.includes(assertion.standing);
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
                          className={`chip rq-evidence rq-evidence--${assertion.evidence_status}`}
                        >
                          {EVIDENCE_LABELS[assertion.evidence_status]}
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
                        Suggested by {authorName(assertion.author_user_id)} ·{" "}
                        {formatDate(assertion.created_at)}
                      </p>

                      <div className="rq-card__summary">
                        {summary ? (
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
                            {assertion.current_revision_number === null
                              ? "No revision to rate yet."
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
                              // latter onto it here (display chips elsewhere still
                              // use the real evidence_status).
                              evidenceStatus:
                                assertion.evidence_status === "awaiting_evidence"
                                  ? "unsupported"
                                  : assertion.evidence_status,
                              currentRevisionNumber:
                                assertion.current_revision_number ?? undefined,
                            }}
                            onAccept={(payload) =>
                              void runReviewAction(() =>
                                api.acceptAssertion(
                                  assertion.id,
                                  payload?.justification?.trim()
                                    ? payload.justification
                                    : undefined,
                                ),
                              )
                            }
                            onReject={() =>
                              void runReviewAction(() =>
                                api.rejectAssertion(assertion.id),
                              )
                            }
                            onDispute={() =>
                              void runReviewAction(() =>
                                api.disputeAssertion(assertion.id),
                              )
                            }
                            onRequestRevision={({ comment }) =>
                              void runReviewAction(() =>
                                api.requestRevision(assertion.id, comment),
                              )
                            }
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
