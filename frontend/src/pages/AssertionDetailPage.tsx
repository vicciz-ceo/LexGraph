import { AssertionEditor } from "../components/AssertionEditor";
// Assertion detail — the full record for one assertion: proposition,
// entities, model provenance, evidence spans, discussion, review history,
// revision activity, team ratings and rationales, and role-gated review
// actions.
//
// Domain rules honored here: user strength ratings (1-5, per revision),
// model confidence (0-1, model/system origins only), and review status
// are three separate indicators and are never merged.
//
// People are named from the matter roster (GET /matters/{id}/members, which
// every member may read); a user id is never a person's label (ui:0).
//
// Collaboration after creation (findings ui:15, pipeline:8), each offered
// only to the members the spec allows: attaching and removing evidence
// follows the edit rule (the author of an unreviewed assertion, or a
// reviewer/admin); members who may comment reply to comments and edit or
// delete their own; any member compares two revisions; reviewers and admins
// supersede an accepted assertion with another accepted one. The API's own
// checks still apply, and a refusal is shown where the action was taken.

import "../styles/pages/assertion-detail.css";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";

import { ApiError, api } from "../api/client";
import { formatInstantDate, formatInstantDateTime } from "../api/datetime";
import type {
  AssertionDetail,
  AssertionListParams,
  AssertionOrigin,
  EntityRef,
  EvidenceStatus,
  HistoryEvent,
  MatterRoleName,
  Rating,
  RatingSummary,
  RelatedMatchList,
  Revision,
} from "../api/types";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession, useSession } from "../app/session";
import { AssertionComments } from "../components/AssertionComments";
import type { AssertionCommentItem } from "../components/AssertionComments";
import { AssertionComparisonView } from "../components/AssertionComparisonView";
import type {
  AssertionComparisonField,
  AssertionComparisonRevision,
} from "../components/AssertionComparisonView";
import { AssertionEvidenceSelector } from "../components/AssertionEvidenceSelector";
import type {
  AssertionEvidenceItem,
  NewEvidenceInput,
} from "../components/AssertionEvidenceSelector";
import { AssertionRevisionHistory } from "../components/AssertionRevisionHistory";
import { AssertionSupersedePanel } from "../components/AssertionSupersedePanel";
import type { SupersedeCandidate } from "../components/AssertionSupersedePanel";
import { SUPPORTING_EVIDENCE_ROLES, UNREVIEWED_STATUSES } from "../constants/evidence";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";
import { AssertionRatingRationales } from "../components/AssertionRatingRationales";
import { AssertionRatingWidget } from "../components/AssertionRatingWidget";
import type { AssertionRatingWidgetSaveData } from "../components/AssertionRatingWidget";
import { AssertionReviewHistory } from "../components/AssertionReviewHistory";
import { AssertionReviewPanel } from "../components/AssertionReviewPanel";
import type { ReviewDecisionOutcome } from "../components/AssertionReviewPanel";
import { isSystemDerived, SYSTEM_DERIVED_LABEL } from "../constants/pipeline";
import { REVIEW_EVIDENCE_REMOVED_MESSAGE, reviewConflictNotice } from "../constants/review";

const ORIGIN_CHIP: Record<AssertionOrigin, { className: string; label: string }> = {
  user_suggested: { className: "chip chip--user", label: "Colleague" },
  model_suggested: { className: "chip chip--model", label: "AI-deduced" },
  system_generated: { className: "chip chip--system", label: "System" },
};

const EVIDENCE_STATUS_BADGE: Record<EvidenceStatus, { className: string; label: string }> = {
  evidenced: { className: "badge badge--accepted", label: "Evidenced" },
  unsupported: { className: "badge badge--rejected", label: "Unsupported" },
  awaiting_evidence: { className: "badge badge--proposed", label: "Awaiting evidence" },
};

// Finding ui:4: system_generated assertions come from the deterministic
// definition-linking pipeline (backend/app/definition_links), which stores
// them accepted, without evidence spans and without a revision record. They
// are not "awaiting evidence", and the user the pipeline run is attributed to
// did not author them. The Review Queue and Contested say the same
// (constants/pipeline.ts).
const SYSTEM_DERIVED_BADGE = { className: "badge badge--neutral", label: SYSTEM_DERIVED_LABEL };

/** Entity types the backend persists, and therefore labels (ui:30). */
const PERSISTED_ENTITY_TYPES = new Set(["Document", "Article", "Definition", "SourceSpan", "Assertion"]);

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const RATING_DISCLAIMER =
  "Ratings reflect users' individual assessments and do not constitute formal legal conclusions.";

const STANDING_EXPLANATION: Record<string, string> = {
  proposed: "Not enough team ratings yet to derive a standing.",
  weak: "Derived from team strength ratings on the current revision: weak support.",
  probable: "Derived from team strength ratings on the current revision: probable support.",
  strong: "Derived from team strength ratings on the current revision: strong support.",
};

const MATCH_KIND_LABEL: Record<string, string> = {
  exact_proposition: "Exact proposition match",
  same_subject_type_object: "Same subject, type & object",
  similar: "Similar proposition",
};

function labelize(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** An instant from the API (created, updated, reviewed, rated) as a date in
 * the viewer's timezone; an offset-less instant is read as UTC. */
function fmtDate(iso: string | null): string {
  return formatInstantDate(iso);
}

/** An instant from the API with its time, in the viewer's timezone. */
function fmtDateTime(iso: string): string {
  return formatInstantDateTime(iso, undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** effective_from / effective_to: a calendar date, shown as written and
 * never shifted by the viewer's offset (unlike the instants above). */
function fmtCalendarDate(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** A short handle for an opaque reference; the full id stays in the tooltip. */
function shortRef(id: string): string {
  if (UUID_PATTERN.test(id)) return id.slice(0, 8);
  return id.length > 24 ? `${id.slice(0, 8)}…` : id;
}

/** At most this many search results are offered as a replacement. */
const SUPERSEDE_SEARCH_LIMIT = 25;

const LAST_SUPPORT_REASON =
  "An accepted assertion keeps at least one supporting passage. Attach another supporting passage first, or return the assertion to review.";

/**
 * An entity as one revision recorded it, worded like EntityChip. Only the
 * assertion's current subject and object carry labels, so an entity that is
 * neither (an earlier subject, say) is shown by type and short reference.
 */
function revisionEntityText(ref: EntityRef | null, detail: AssertionDetail): string {
  if (!ref || (ref.type === null && ref.id === null)) return "None";
  const type = ref.type ?? "Entity";
  const current = [detail.subject_entity, detail.object_entity].find(
    (known) => known && known.type === ref.type && known.id === ref.id,
  );
  if (current) {
    const label = current.label?.trim();
    if (label) return `${type}: ${label}`;
    if (ref.type !== null && PERSISTED_ENTITY_TYPES.has(ref.type)) {
      return `${type}: not available in this matter`;
    }
    return ref.id ? `${type}: external reference ${shortRef(ref.id)}` : type;
  }
  return ref.id ? `${type} ${shortRef(ref.id)}` : type;
}

/** The same instant compares equal however the server spelled it. */
function instantIdentity(iso: string | null): string {
  if (!iso) return "";
  const time = Date.parse(iso);
  return Number.isNaN(time) ? iso : String(time);
}

/** The fields a revision records besides its text (spec §3), for comparison. */
function revisionFields(revision: Revision, detail: AssertionDetail): AssertionComparisonField[] {
  const entityIdentity = (ref: EntityRef | null) => (ref ? `${ref.type}\u0000${ref.id}` : "");
  return [
    { key: "assertion_type", label: "Assertion type", value: labelize(revision.assertion_type) },
    {
      key: "subject",
      label: "Subject",
      value: revisionEntityText(revision.subject_entity, detail),
      identity: entityIdentity(revision.subject_entity),
    },
    {
      key: "object",
      label: "Object",
      value: revisionEntityText(revision.object_entity, detail),
      identity: entityIdentity(revision.object_entity),
    },
    { key: "jurisdiction", label: "Jurisdiction", value: revision.jurisdiction ?? "—" },
    {
      key: "effective_from",
      label: "Effective from",
      value: fmtCalendarDate(revision.effective_from),
      identity: instantIdentity(revision.effective_from),
    },
    {
      key: "effective_to",
      label: "Effective to",
      value: fmtCalendarDate(revision.effective_to),
      identity: instantIdentity(revision.effective_to),
    },
  ];
}

/** The current revision's number, or null when no revision record backs it. */
function recordedCurrentRevision(assertion: AssertionDetail): number | null {
  const current = assertion.current_revision_number;
  if (current == null) return null;
  return assertion.revision_history.some((r) => r.revision_number === current) ? current : null;
}

function EntityChip({ entity }: { entity: EntityRef }): ReactElement {
  const type = entity.type ?? "Entity";
  const label = entity.label && entity.label.trim() ? entity.label : null;
  const title = entity.id ? `${type} ${entity.id}` : undefined;
  const typeTag = (
    <span className="adp-entity-type">
      {type}
      <span className="adp-sr-only">: </span>
    </span>
  );
  if (label) {
    const body = (
      <>
        {typeTag}
        <span className="adp-entity-label">{label}</span>
      </>
    );
    return entity.type === "Assertion" && entity.id ? (
      <Link to={`/assertions/${encodeURIComponent(entity.id)}`} className="adp-entity" title={title}>
        {body}
      </Link>
    ) : (
      <span className="adp-entity" title={title}>
        {body}
      </span>
    );
  }
  return (
    <span className="adp-entity" title={title}>
      {typeTag}
      {entity.type !== null && PERSISTED_ENTITY_TYPES.has(entity.type) ? (
        <span className="adp-entity-ref muted">Not available in this matter</span>
      ) : (
        <span className="adp-entity-ref muted">
          External reference
          {entity.id && <span className="mono">{shortRef(entity.id)}</span>}
        </span>
      )}
    </span>
  );
}

type Unavailable = "missing" | "forbidden";

interface OtherMatter {
  id: string;
  /** null when the matter is not in this session's matter list. */
  name: string | null;
}

interface SwitchNotice {
  assertionId: string;
  matterId: string;
  fromName: string;
  toName: string;
}

/** Two revisions of one assertion shown side by side under Activity. */
interface Comparison {
  assertionId: string;
  left: number;
  right: number;
}

export function AssertionDetailPage({ assertionId }: { assertionId: string }) {
  const session = useActiveSession();
  const { selectMatter } = useSession();
  const role = session.role;
  const canContribute = role === "contributor" || role === "reviewer" || role === "admin";
  const canReview = role === "reviewer" || role === "admin";

  const [detail, setDetail] = useState<AssertionDetail | null>(null);
  // At most the 20 strongest matches; `total` counts them all when known.
  const [related, setRelated] = useState<RelatedMatchList>([]);
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  // `null` = the request failed (the page says so instead of showing nothing).
  const [ratings, setRatings] = useState<Rating[] | null>([]);
  const [history, setHistory] = useState<HistoryEvent[] | null>([]);
  const [memberNames, setMemberNames] = useState<Record<string, string> | null>(null);
  const [memberRoles, setMemberRoles] = useState<Record<string, MatterRoleName> | null>(null);
  // The assertion that superseded this one, when it could be loaded.
  const [successor, setSuccessor] = useState<AssertionDetail | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  // Rating summaries for compared revisions, by "<assertion id>:<revision>";
  // null when one could not be loaded.
  const [revisionSummaries, setRevisionSummaries] = useState<Record<string, RatingSummary | null>>({});
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState<Unavailable | null>(null);
  const [otherMatter, setOtherMatter] = useState<OtherMatter | null>(null);
  const [switchNotice, setSwitchNotice] = useState<SwitchNotice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  // Review fe-review-detail:0: from a review decision until the page shows
  // the record re-read after it, the review panel stays disabled. Until then
  // the page still shows the old status, so a second click of a double-click
  // would repeat the decision (refused with 409) or apply another one to a
  // status the reviewer never saw. Only a read started after the decision
  // settled (awaitingDecisionReload was set) ends it.
  const [deciding, setDeciding] = useState(false);
  const awaitingDecisionReload = useRef(false);
  // Review fe-review-detail:7: bumped whenever the page re-reads the current
  // revision's ratings, so that revision's ratings under Activity, once
  // loaded, are read again and agree with the Ratings card.
  const [ratingsVersion, setRatingsVersion] = useState(0);
  // Finding ui:31 / review:11: the assertion last shown in the active matter,
  // and the one this page already switched matter for. A link into another of
  // the user's matters switches once; a user who then switches matter away
  // from the assertion on screen is offered a button, not switched back.
  const shownRef = useRef<string | null>(null);
  const switchedForRef = useRef<string | null>(null);

  const refresh = useCallback(() => setReloadKey((key) => key + 1), []);

  // The current revision's ratings were read again (on every load of the
  // record and after the user rates): its ratings under Activity, once
  // loaded, and an open comparison that includes it follow (fe-review-detail:7).
  const showRevisionRatings = (id: string, revision: number, sum: RatingSummary | null) => {
    setRatingsVersion((version) => version + 1);
    if (sum === null) return;
    const key = `${id}:${revision}`;
    setRevisionSummaries((current) => (key in current ? { ...current, [key]: sum } : current));
  };

  // Hard reset when the target assertion (or active matter) changes.
  useEffect(() => {
    setDetail(null);
    setSummary(null);
    setRelated([]);
    setRatings([]);
    setHistory([]);
    setMemberNames(null);
    setMemberRoles(null);
    setSuccessor(null);
    setComparison(null);
    setUnavailable(null);
    setOtherMatter(null);
    setActionError(null);
    setDeciding(false);
    setLoading(true);
  }, [assertionId, session.currentMatter.id]);

  useEffect(() => {
    let cancelled = false;
    const matterId = session.currentMatter.id;
    // This read shows the result of a review decision that has just settled.
    const showsDecision = awaitingDecisionReload.current;
    setError(null);
    (async () => {
      try {
        const assertion = await api.getAssertion(assertionId);
        if (cancelled) return;
        if (assertion.matter_id !== matterId) {
          const target = session.matters.find((m) => m.id === assertion.matter_id) ?? null;
          if (target && shownRef.current !== assertionId && switchedForRef.current !== assertionId) {
            switchedForRef.current = assertionId;
            setSwitchNotice({
              assertionId,
              matterId: target.id,
              fromName: session.currentMatter.name,
              toName: target.name,
            });
            selectMatter(target.id);
            return;
          }
          setDetail(null);
          setOtherMatter({ id: assertion.matter_id, name: target?.name ?? null });
          return;
        }
        const revision = recordedCurrentRevision(assertion);
        const successorId =
          assertion.status === "superseded" ? assertion.superseded_by_assertion_id : null;
        const [rel, sum, rows, events, roster, replacement] = await Promise.all([
          api.relatedAssertions(assertionId).catch((): RelatedMatchList => []),
          revision != null
            ? api.ratingSummary(assertionId, revision).catch(() => null)
            : Promise.resolve(null),
          revision != null
            ? api.listRatings(assertionId, revision).catch(() => null)
            : Promise.resolve([] as Rating[]),
          api.history(assertionId).catch(() => null),
          api.listMatterMembers(matterId).catch(() => null),
          // The page links the replacement either way; loading it only adds its text.
          successorId ? api.getAssertion(successorId).catch(() => null) : Promise.resolve(null),
        ]);
        if (cancelled) return;
        shownRef.current = assertionId;
        setDetail(assertion);
        setRelated(rel);
        setSummary(sum);
        setRatings(rows);
        if (revision != null) showRevisionRatings(assertionId, revision, sum);
        setHistory(events);
        setSuccessor(replacement);
        // A failed roster refresh keeps the names already known.
        if (roster) {
          setMemberNames(Object.fromEntries(roster.map((m) => [m.user.id, m.user.display_name])));
          setMemberRoles(Object.fromEntries(roster.map((m) => [m.user.id, m.role])));
        }
        setOtherMatter(null);
        setUnavailable(null);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 404 || err.status === 403)) {
          setDetail(null);
          setUnavailable(err.status === 404 ? "missing" : "forbidden");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load assertion.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          // In the render that shows the re-read record (or why it failed).
          if (showsDecision) {
            awaitingDecisionReload.current = false;
            setDeciding(false);
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // session.matters/selectMatter are read when the active matter changes.
  }, [assertionId, session.currentMatter.id, reloadKey]);

  // ui:0: never a user id. A former member is no longer on the roster; with
  // no roster at all (request failed) only a neutral label is possible.
  const nameFor = useCallback(
    (userId: string) => {
      if (userId === session.user.id) return session.user.display_name;
      if (memberNames === null) return "Team member";
      return memberNames[userId] ?? "Former member";
    },
    [session.user.id, session.user.display_name, memberNames],
  );

  // Replacement candidates for a supersede: accepted assertions of this
  // matter, never this assertion or one whose supersede link already points
  // back at it.
  const searchSuccessors = useCallback(
    async (q: string): Promise<SupersedeCandidate[]> => {
      // A replacement is usually recent: the newest matches come first, and
      // a narrower search finds older ones.
      const query: AssertionListParams = {
        q,
        status: "accepted",
        sort: "-created_at",
        limit: SUPERSEDE_SEARCH_LIMIT,
      };
      const result = await api.listAssertions(session.currentMatter.id, query);
      return result.items
        .filter(
          (item) =>
            item.id !== assertionId &&
            item.status === "accepted" &&
            item.superseded_by_assertion_id !== assertionId,
        )
        .slice(0, SUPERSEDE_SEARCH_LIMIT)
        .map((item) => ({ id: item.id, proposition: item.proposition }));
    },
    [assertionId, session.currentMatter.id],
  );

  // After a rating change: re-read the record, then the summary and the
  // rationales of its current revision, and show them together. The rating
  // itself was saved, so a failed re-read reloads the page data instead of
  // reporting the save as failed.
  const reloadRatings = async (id: string) => {
    try {
      const fresh = await api.getAssertion(id);
      const revision = recordedCurrentRevision(fresh);
      const [sum, rows] = await Promise.all([
        revision != null ? api.ratingSummary(id, revision) : Promise.resolve(null),
        revision != null
          ? api.listRatings(id, revision).catch(() => null)
          : Promise.resolve([] as Rating[]),
      ]);
      setDetail(fresh);
      setSummary(sum);
      setRatings(rows);
      if (revision != null) showRevisionRatings(id, revision, sum);
    } catch {
      refresh();
    }
  };

  // listing:0: `rationale` is present only when the user edited the box, so
  // an untouched one leaves the stored rationale as it is (spec §13).
  const handleSaveRating = async ({ strength, rationale }: AssertionRatingWidgetSaveData) => {
    if (!detail || detail.current_revision_number == null) return;
    await api.putRating(detail.id, detail.current_revision_number, strength, rationale);
    await reloadRatings(detail.id);
  };

  const handleRemoveRating = async () => {
    if (!detail || detail.current_revision_number == null) return;
    await api.deleteRating(detail.id, detail.current_revision_number);
    await reloadRatings(detail.id);
  };

  // Re-reads the record after a review decision settled; the review panel
  // stays disabled (`deciding`) until the page shows it.
  const reloadAfterDecision = () => {
    awaitingDecisionReload.current = true;
    refresh();
  };

  // Resolves to whether the decision was recorded; the review panel keeps
  // its form (and blocks a second decision) until it settles, and the page
  // keeps the panel disabled until the record re-read after it is shown.
  const runReview = async (
    action: () => Promise<unknown>,
    { acceptWithoutJustification = false }: { acceptWithoutJustification?: boolean } = {},
  ): Promise<ReviewDecisionOutcome> => {
    setActionError(null);
    setDeciding(true);
    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Stale record (edited, withdrawn or decided meanwhile): nothing was
        // recorded. Say so and show the current version.
        setActionError(reviewConflictNotice(err.message));
        reloadAfterDecision();
        return false;
      }
      if (err instanceof ApiError && err.status === 422 && acceptWithoutJustification) {
        // fe-review-detail:2: the page showed supporting evidence that was
        // removed after it loaded (that changes neither the revision nor
        // updated_at). Nothing was recorded: say so, show the current
        // evidence and ask for the justification.
        setActionError(REVIEW_EVIDENCE_REMOVED_MESSAGE);
        reloadAfterDecision();
        return "needs-justification";
      }
      setDeciding(false);
      setActionError(err instanceof Error ? err.message : "Review action failed.");
      return false;
    }
    reloadAfterDecision();
    return true;
  };

  // --- Comments (spec §9). AssertionComments shows a refused action's reason
  // (blank or markup-only text, a viewer role, someone else's comment) in the
  // form it came from and keeps the typed text.
  const commentGone = (err: unknown): unknown =>
    err instanceof ApiError && err.status === 404
      ? new Error("This comment no longer exists. Reload the page to see the current discussion.")
      : err;

  const handleAddComment = async (text: string) => {
    if (!detail) return;
    await api.addComment(detail.id, text);
    refresh();
  };

  const handleReplyToComment = async (parentCommentId: string, text: string) => {
    if (!detail) return;
    try {
      await api.addComment(detail.id, text, parentCommentId);
    } catch (err) {
      throw commentGone(err);
    }
    refresh();
  };

  const handleEditComment = async (commentId: string, text: string) => {
    if (!detail) return;
    try {
      await api.updateComment(detail.id, commentId, text);
    } catch (err) {
      throw commentGone(err);
    }
    refresh();
  };

  const handleDeleteComment = async (commentId: string) => {
    if (!detail) return;
    try {
      await api.deleteComment(detail.id, commentId);
    } catch (err) {
      throw commentGone(err);
    }
    refresh();
  };

  // --- Evidence after creation (spec §8, §10). The selector shows the
  // server's reason for a refused change. After a refusal (403), a passage
  // removed meanwhile (404) or a conflict (409) the record is re-read, so the
  // card shows the current evidence and controls.
  const runEvidenceChange = async (change: () => Promise<unknown>) => {
    try {
      await change();
    } catch (err) {
      if (err instanceof ApiError && [403, 404, 409].includes(err.status)) refresh();
      throw err;
    }
    refresh();
  };

  const handleAddEvidence = async ({ sourceSpanId, evidenceRole }: NewEvidenceInput) => {
    if (!detail) return;
    const id = detail.id;
    await runEvidenceChange(() => api.addEvidence(id, sourceSpanId, evidenceRole));
  };

  const handleRemoveEvidence = async (evidenceId: string) => {
    if (!detail) return;
    const id = detail.id;
    await runEvidenceChange(() => api.removeEvidence(id, evidenceId));
  };

  // --- Supersede (reviewers and admins, accepted assertions). Like the other
  // review decisions it names the revision on screen, so the API refuses it
  // (409) if the assertion changed meanwhile; the page then says the
  // decision was not recorded and shows the current version. The panel
  // shows the server's reason for any refusal and keeps the choice. The
  // review panel stays disabled until the page shows the result
  // (fe-review-detail:0).
  const handleSupersede = async (successorId: string) => {
    if (!detail) return;
    setActionError(null);
    setDeciding(true);
    try {
      await api.supersedeAssertion(detail.id, successorId, detail.current_revision_number);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setActionError(reviewConflictNotice(err.message));
        reloadAfterDecision();
      } else {
        setDeciding(false);
      }
      throw err;
    }
    reloadAfterDecision();
  };

  // --- Revision comparison (spec §3): both revisions' rating summaries are
  // read again on every comparison; a failed one is shown as such.
  const handleCompare = (left: number, right: number) => {
    if (!detail) return;
    const id = detail.id;
    setComparison({ assertionId: id, left, right });
    void Promise.all(
      [left, right].map((revisionNumber) => api.ratingSummary(id, revisionNumber).catch(() => null)),
    ).then(([leftSummary, rightSummary]) =>
      setRevisionSummaries((current) => ({
        ...current,
        [`${id}:${left}`]: leftSummary,
        [`${id}:${right}`]: rightSummary,
      })),
    );
  };

  const backLink = (
    <Link to="/review" className="adp-back">
      <Icon name="arrow-back" size={16} />
      Back to Review Queue
    </Link>
  );

  if (unavailable) {
    return (
      <div>
        {backLink}
        <div className="empty-state">
          {unavailable === "missing" ? (
            <>
              <p className="empty-state__title">Assertion not found</p>
              <p>This assertion does not exist.</p>
            </>
          ) : (
            <>
              <p className="empty-state__title">Assertion not available</p>
              <p>
                This assertion belongs to a matter you are not a member of. Ask a matter admin for
                access.
              </p>
            </>
          )}
        </div>
      </div>
    );
  }

  if (otherMatter) {
    return (
      <div>
        {backLink}
        <div className="empty-state">
          <p className="empty-state__title">Assertion in another matter</p>
          {otherMatter.name ? (
            <>
              <p>
                {`This assertion belongs to ${otherMatter.name}, not the active matter ${session.currentMatter.name}.`}
              </p>
              <button
                type="button"
                className="btn btn--primary btn--sm adp-switch-matter"
                onClick={() => selectMatter(otherMatter.id)}
              >
                {`Switch to ${otherMatter.name}`}
              </button>
            </>
          ) : (
            <p>
              This assertion belongs to a matter that is not in your matter list. Reload the page
              to refresh your matter memberships.
            </p>
          )}
        </div>
      </div>
    );
  }

  if (!detail) {
    if (error) {
      return (
        <div>
          {backLink}
          <div className="error-banner" role="alert">
            {error}
          </div>
          <button type="button" className="btn btn--secondary" onClick={refresh}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="loading">Loading assertion…</div>;
  }

  const origin = ORIGIN_CHIP[detail.origin];
  const isSystem = detail.origin === "system_generated";
  const evidenceStatus = isSystemDerived(detail)
    ? SYSTEM_DERIVED_BADGE
    : EVIDENCE_STATUS_BADGE[detail.evidence_status];
  const showStanding = detail.standing !== detail.status;
  const isModelOrigin =
    detail.origin === "model_suggested" || detail.origin === "system_generated";
  const showRawProposition =
    detail.proposition_raw !== null && detail.proposition_raw !== detail.proposition;

  const effectiveWindow =
    detail.effective_from === null && detail.effective_to === null
      ? "—"
      : `${detail.effective_from ? fmtCalendarDate(detail.effective_from) : "…"} – ${
          detail.effective_to ? fmtCalendarDate(detail.effective_to) : "ongoing"
        }`;

  const distributionSummary = summary ??
    detail.ratings_summary ?? { count: 0, average: null, median: null, distribution: {} };

  // ui:12: compare with earlier revisions (the server counts their ratings),
  // never with detail.ratings_summary, which describes the same revision.
  const ratedRevision = recordedCurrentRevision(detail);
  const priorRatingCount = summary?.prior_revision_rating_count ?? 0;
  const hasRatingsOnPriorRevision =
    summary !== null && summary.count === 0 && priorRatingCount > 0;

  // listing:0: the rating editor starts from the viewer's stored rating of
  // the current revision: the summary's current_user_rating, else their row
  // in the rating list (which lists every rating of the revision, with the
  // rater's own rationale). When neither could be read the stored rating is
  // unknown, and the page offers no editor that would replace it blind.
  const ownRow = ratings?.find((row) => row.user_id === session.user.id) ?? null;
  const ownRating: { strength: number | null; rationale: string } | null =
    summary !== null
      ? {
          strength: summary.current_user_rating?.strength ?? null,
          // review:7: the exact text, as written.
          rationale:
            summary.current_user_rating?.rationale_raw ??
            summary.current_user_rating?.rationale ??
            "",
        }
      : ratings !== null
        ? {
            strength: ownRow?.strength ?? null,
            rationale: ownRow?.rationale_raw ?? ownRow?.rationale ?? "",
          }
        : null;

  const authorLabel = isSystem
    ? "System (definition-linking pipeline)"
    : nameFor(detail.author_user_id);
  const showSwitchNotice =
    switchNotice !== null &&
    switchNotice.assertionId === assertionId &&
    switchNotice.matterId === session.currentMatter.id;

  const revisions = [...detail.revision_history].sort(
    (a, b) => b.revision_number - a.revision_number,
  );

  // Evidence controls follow the edit rule (spec §12): the author, with
  // contributor membership, while the assertion is unreviewed, or a
  // reviewer/admin. An accepted assertion keeps its last supporting passage,
  // so the page never makes it unsupported (spec §2).
  const isAuthor = detail.author_user_id === session.user.id;
  const canModifyEvidence =
    canReview || (role === "contributor" && isAuthor && UNREVIEWED_STATUSES.has(detail.status));
  const supportingCount = detail.evidence.filter((item) =>
    SUPPORTING_EVIDENCE_ROLES.has(item.evidence_role),
  ).length;
  const evidenceItems: AssertionEvidenceItem[] = detail.evidence.map((item) => ({
    id: item.id,
    sourceSpanId: item.source_span_id,
    evidenceRole: item.evidence_role,
    quote: item.quote_text ?? "",
    documentTitle: item.document_title ?? null,
    addedBy: nameFor(item.added_by_user_id),
  }));
  const evidenceRemovalBlocked = (item: AssertionEvidenceItem): string | null =>
    detail.status === "accepted" &&
    SUPPORTING_EVIDENCE_ROLES.has(item.evidenceRole) &&
    supportingCount <= 1
      ? LAST_SUPPORT_REASON
      : null;

  // Spec §9: reviewer comments are visually distinguishable. The badge
  // follows the author's current role in the matter.
  const reviewerLabelFor = (userId: string): string | null => {
    const memberRole = memberRoles?.[userId] ?? (userId === session.user.id ? role : undefined);
    if (memberRole === "admin") return "Admin";
    if (memberRole === "reviewer") return "Reviewer";
    return null;
  };
  const commentItems: AssertionCommentItem[] = detail.comments.map((comment) => {
    const reviewerLabel = reviewerLabelFor(comment.user_id);
    return {
      id: comment.id,
      userId: comment.user_id,
      authorName: nameFor(comment.user_id),
      commentText: comment.comment_text,
      commentTextRaw: comment.comment_text_raw,
      isReviewer: reviewerLabel !== null,
      reviewerLabel: reviewerLabel ?? undefined,
      parentCommentId: comment.parent_comment_id,
      createdAt: comment.created_at,
      updatedAt: comment.updated_at,
      deletedAt: comment.deleted_at,
    };
  });
  const liveCommentCount = detail.comments.filter((comment) => !comment.deleted_at).length;

  const revisionItems = revisions.map((revision) => ({
    revisionNumber: revision.revision_number,
    proposition: revision.proposition,
    propositionRaw: revision.proposition_raw ?? undefined,
    editedBy: nameFor(revision.edited_by_user_id),
    createdAt: fmtDateTime(revision.created_at),
    revisionReason: revision.revision_reason,
  }));
  const compared = (revision: Revision): AssertionComparisonRevision => ({
    revisionNumber: revision.revision_number,
    proposition: revision.proposition,
    propositionRaw: revision.proposition_raw ?? undefined,
    editedBy: nameFor(revision.edited_by_user_id),
    createdAt: fmtDateTime(revision.created_at),
    revisionReason: revision.revision_reason,
    fields: revisionFields(revision, detail),
  });
  const shownComparison = comparison !== null && comparison.assertionId === detail.id ? comparison : null;
  const compareLeft = shownComparison
    ? detail.revision_history.find((r) => r.revision_number === shownComparison.left)
    : undefined;
  const compareRight = shownComparison
    ? detail.revision_history.find((r) => r.revision_number === shownComparison.right)
    : undefined;

  // Supersede (spec §1, §10): reviewers and admins, on an accepted
  // assertion, with another accepted assertion of this matter.
  const canSupersede = canReview && detail.status === "accepted";
  const supersedeSuggestions: SupersedeCandidate[] = related
    .filter((match) => match.status === "accepted" && match.assertion_id !== detail.id && match.proposition)
    .map((match) => ({ id: match.assertion_id, proposition: match.proposition ?? "" }));
  const supersededBy = detail.status === "superseded" ? detail.superseded_by_assertion_id : null;
  const shownSuccessor = supersededBy && successor?.id === supersededBy ? successor : null;

  return (
    <div className="adp">
      {backLink}

      <header className="page-header adp-header">
        <div>
          <h1 className="page-header__title">Assertion</h1>
          <div className="adp-meta">
            <span className={`badge badge--${detail.status}`}>{labelize(detail.status)}</span>
            {showStanding && (
              <span className={`badge badge--${detail.standing}`}>
                {labelize(detail.standing)}
              </span>
            )}
            <span className={origin.className}>{origin.label}</span>
            <span className="mono">{detail.id}</span>
            <span className="muted">Created {fmtDate(detail.created_at)}</span>
            <span className="muted">Updated {fmtDate(detail.updated_at)}</span>
          </div>
          <div className="adp-byline">
            <span>Author: {authorLabel}</span>
            {isSystem && (
              <span className="muted">Pipeline run attributed to {nameFor(detail.author_user_id)}</span>
            )}
            {detail.reviewed_by && (
              <span>
                Last reviewed by {nameFor(detail.reviewed_by)} on {fmtDate(detail.reviewed_at)}
              </span>
            )}
          </div>
        </div>
      </header>

      {showSwitchNotice && switchNotice && (
        <p className="adp-notice" role="status">
          {`Switched the active matter from ${switchNotice.fromName} to ${switchNotice.toName} to show this assertion.`}
        </p>
      )}
      {supersededBy && (
        <p className="adp-notice adp-superseded-notice" role="note">
          Superseded by{" "}
          <Link to={`/assertions/${encodeURIComponent(supersededBy)}`}>
            {shownSuccessor ? shownSuccessor.proposition : "the superseding assertion"}
          </Link>
          {shownSuccessor && (
            <>
              {" "}
              <span className={`badge badge--${shownSuccessor.status}`}>
                {labelize(shownSuccessor.status)}
              </span>
            </>
          )}
        </p>
      )}
      {loading && <div className="adp-refreshing muted">Refreshing…</div>}
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {actionError && (
        <div className="error-banner" role="alert">
          {actionError}
        </div>
      )}

      <div className="adp-layout">
        <div className="adp-col adp-col--main">
          <section className="card">
            <div className="card__header">Proposition</div>
            <div className="card__body">
              <p className="adp-proposition">{detail.proposition}</p>
              {showRawProposition && (
                <details className="adp-raw">
                  <summary>Authored text</summary>
                  <p className="adp-raw-text">{detail.proposition_raw}</p>
                </details>
              )}
              <div className="adp-entities">
                <EntityChip entity={detail.subject_entity} />
                <span className="adp-relation">
                  {labelize(detail.assertion_type)}
                  <Icon name="chevron-right" size={14} />
                </span>
                {detail.object_entity && <EntityChip entity={detail.object_entity} />}
              </div>
              <dl className="adp-facts">
                <div className="adp-fact">
                  <dt>Jurisdiction</dt>
                  <dd>{detail.jurisdiction ?? "—"}</dd>
                </div>
                <div className="adp-fact">
                  <dt>Effective</dt>
                  <dd>{effectiveWindow}</dd>
                </div>
                {detail.current_revision_number != null && (
                  <div className="adp-fact">
                    <dt>Revision</dt>
                    <dd>v{detail.current_revision_number}</dd>
                  </div>
                )}
              </dl>
            </div>
          </section>

          {canContribute && <AssertionEditor key={detail.id} detail={detail} canReview={canReview}
            isAuthor={detail.author_user_id === session.user.id} onSaved={refresh} />}
          {canContribute && <Link to="/suggest" className="btn btn--secondary">Suggest another assertion</Link>}

          {isModelOrigin && (
            <section className="card">
              <div className="card__header">{isSystem ? "Pipeline provenance" : "Model provenance"}</div>
              <div className="card__body adp-provenance">
                <div className="adp-provenance-row">
                  <span className={origin.className}>{origin.label}</span>
                  <span className="adp-confidence">
                    {isSystem ? "Pipeline confidence:" : "Model confidence:"}{" "}
                    <strong>
                      {detail.confidence != null
                        ? `${Math.round(detail.confidence * 100)}%`
                        : "Not applicable"}
                    </strong>
                  </span>
                </div>
                {detail.agent_provenance && <p>
                  Platform: {detail.agent_provenance.platform}
                  {detail.agent_provenance.model && ` · Model: ${detail.agent_provenance.model}`}
                  {detail.agent_provenance.run_id && ` · Run: ${detail.agent_provenance.run_id}`}
                  {" (self-reported)"}
                </p>}
                {isSystem ? (
                  <p className="adp-note">
                    Generated automatically by LexGraph&apos;s deterministic definition-linking
                    pipeline; no person or language model suggested it. The confidence is the
                    pipeline&apos;s own score for this kind of link. It is independent of team
                    strength ratings and of the review status.
                  </p>
                ) : (
                  <p className="adp-note">
                    Model confidence is reported by the extraction pipeline. It is independent
                    of team strength ratings and of the review status.
                  </p>
                )}
              </div>
            </section>
          )}

          <section className="card" aria-labelledby="adp-evidence-title">
            <div className="card__header">
              <span id="adp-evidence-title">Evidence</span>
              <span className={evidenceStatus.className}>{evidenceStatus.label}</span>
            </div>
            <div className="card__body">
              <AssertionEvidenceSelector
                key={detail.id}
                matterId={detail.matter_id}
                evidence={evidenceItems}
                onAdd={canModifyEvidence ? handleAddEvidence : undefined}
                onRemove={canModifyEvidence ? handleRemoveEvidence : undefined}
                removalBlockedReason={evidenceRemovalBlocked}
                emptyMessage={
                  isSystem
                    ? "No evidence spans are attached. LexGraph's definition-linking pipeline generated this assertion automatically from the provision text it links (shown above); no person suggested it."
                    : "No evidence spans are linked to this assertion."
                }
              />
            </div>
          </section>

          <section className="card" aria-labelledby="adp-comments-title">
            <div className="card__header">
              <span id="adp-comments-title">Comments</span>
              <span className="muted adp-count">{liveCommentCount}</span>
            </div>
            <div className="card__body">
              <AssertionComments
                key={detail.id}
                comments={commentItems}
                currentUserId={session.user.id}
                canComment={canContribute}
                onAdd={handleAddComment}
                onReply={handleReplyToComment}
                onEdit={handleEditComment}
                onDelete={handleDeleteComment}
                formatTime={fmtDateTime}
              />
            </div>
          </section>

          <section className="card" aria-labelledby="adp-review-history-title">
            <div className="card__header" id="adp-review-history-title">
              Review history
            </div>
            <div className="card__body">
              <AssertionReviewHistory
                events={history}
                nameFor={nameFor}
                formatTime={fmtDateTime}
                systemGenerated={isSystem}
              />
            </div>
          </section>

          <section className="card" aria-labelledby="adp-activity-title">
            <div className="card__header" id="adp-activity-title">
              Activity
            </div>
            <div className="card__body">
              {revisions.length === 0 ? (
                <p className="muted">
                  {isSystem
                    ? "No revisions are recorded. System-generated assertions are created without a revision record; edits made here are recorded as revisions."
                    : "No revisions recorded yet."}
                </p>
              ) : (
                <>
                  <AssertionRevisionHistory
                    key={detail.id}
                    revisions={revisionItems}
                    currentRevisionNumber={detail.current_revision_number}
                    onCompare={handleCompare}
                    renderFooter={(revisionNumber) => (
                      <RevisionRatings
                        assertionId={detail.id}
                        revision={revisionNumber}
                        currentUserId={session.user.id}
                        nameFor={nameFor}
                        version={revisionNumber === ratedRevision ? ratingsVersion : undefined}
                      />
                    )}
                  />
                  {shownComparison && compareLeft && compareRight && (
                    <div className="adp-compare-wrap">
                      <div className="adp-compare-head">
                        <h3 className="adp-subhead">
                          {`Revision ${compareLeft.revision_number} compared with revision ${compareRight.revision_number}`}
                        </h3>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => setComparison(null)}
                        >
                          Close comparison
                        </button>
                      </div>
                      <AssertionComparisonView
                        left={compared(compareLeft)}
                        right={compared(compareRight)}
                        leftRatingSummary={revisionSummaries[`${detail.id}:${compareLeft.revision_number}`]}
                        rightRatingSummary={revisionSummaries[`${detail.id}:${compareRight.revision_number}`]}
                      />
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </div>

        <div className="adp-col adp-col--side">
          <section className="card" aria-labelledby="adp-ratings-title">
            <div className="card__header" id="adp-ratings-title">
              Ratings
            </div>
            <div className="card__body">
              {ratedRevision != null ? (
                <p className="muted adp-rating-scope">
                  Team ratings for revision v{ratedRevision} (current)
                </p>
              ) : (
                detail.current_revision_number != null && (
                  <p className="muted adp-rating-scope">
                    Revision v{detail.current_revision_number} has no stored revision record, so it
                    cannot be rated. An edit records a new revision that can be rated.
                  </p>
                )
              )}
              {hasRatingsOnPriorRevision && (
                <p className="adp-revision-note" role="note">
                  {`${priorRatingCount} earlier ${
                    priorRatingCount === 1 ? "rating was" : "ratings were"
                  } recorded against prior revisions of this assertion. Revision v${ratedRevision} has not been rated yet; earlier ratings stay with their revision under Activity.`}
                </p>
              )}
              <AssertionRatingDistribution
                summary={distributionSummary}
                modelConfidence={null}
                detailed
              />
              {distributionSummary.count > 0 && distributionSummary.median != null && (
                <p className="muted adp-stats">Median {distributionSummary.median}/5</p>
              )}
              <AssertionRatingRationales
                ratings={ratings}
                // Without a summary the list itself counts the ratings.
                ratingCount={summary?.count ?? ratings?.length ?? 0}
                rationaleCount={summary?.rationale_count ?? null}
                currentUserId={session.user.id}
                nameFor={nameFor}
                formatDate={fmtDate}
              />
              {detail.status === "proposed" && (
                <div className="adp-standing">
                  <span className={`badge badge--${detail.standing}`}>
                    {labelize(detail.standing)}
                  </span>
                  <span className="adp-standing-note">
                    {STANDING_EXPLANATION[detail.standing] ??
                      "Standing is derived from team strength ratings."}
                  </span>
                </div>
              )}
              {canContribute && ratedRevision != null && (
                <div className="adp-rating-widget">
                  <h3 className="adp-subhead">
                    Your rating (v{ratedRevision})
                  </h3>
                  {ownRating ? (
                    <AssertionRatingWidget
                      key={`${detail.id}:${ratedRevision}`}
                      currentUserRating={ownRating.strength}
                      currentRationale={ownRating.rationale}
                      onSave={handleSaveRating}
                      onRemove={handleRemoveRating}
                    />
                  ) : (
                    <div className="error-banner" role="alert">
                      Your rating could not be loaded.{" "}
                      <button type="button" className="btn btn--sm btn--secondary" onClick={refresh}>
                        Retry
                      </button>
                    </div>
                  )}
                  <p className="adp-note">
                    Ratings inform standing only — they never change the review status.
                  </p>
                </div>
              )}
              <p className="adp-note adp-disclaimer">{RATING_DISCLAIMER}</p>
            </div>
          </section>

          {canReview && (
            <section className="card">
              <div className="card__header">Review</div>
              <div className="card__body">
                <AssertionReviewPanel
                  assertion={{
                    id: detail.id,
                    status: detail.status,
                    // The backend requires an acceptance justification whenever
                    // there is no supporting evidence, which covers both
                    // "unsupported" and "awaiting_evidence". The panel only
                    // gates on "unsupported", so map the latter onto it here
                    // (the status badge above still uses the real evidence_status).
                    evidenceStatus:
                      detail.evidence_status === "awaiting_evidence"
                        ? "unsupported"
                        : detail.evidence_status,
                    currentRevisionNumber: detail.current_revision_number ?? undefined,
                  }}
                  onAccept={(payload) => {
                    const justification = payload?.justification?.trim() || undefined;
                    return runReview(
                      () =>
                        api.acceptAssertion(
                          detail.id,
                          justification,
                          detail.current_revision_number,
                        ),
                      { acceptWithoutJustification: justification === undefined },
                    );
                  }}
                  onReject={() =>
                    runReview(() => api.rejectAssertion(detail.id, detail.current_revision_number))
                  }
                  onDispute={() =>
                    runReview(() => api.disputeAssertion(detail.id, detail.current_revision_number))
                  }
                  onRequestRevision={(payload) =>
                    runReview(() =>
                      api.requestRevision(
                        detail.id,
                        payload.comment,
                        detail.current_revision_number,
                      ),
                    )
                  }
                  hasRatingsOnPriorRevision={hasRatingsOnPriorRevision}
                  // fe-review-detail:0: until the record re-read after a
                  // decision is on screen.
                  busy={deciding}
                />
              </div>
            </section>
          )}

          {canSupersede && (
            <section className="card" aria-labelledby="adp-supersede-title">
              <div className="card__header" id="adp-supersede-title">
                Supersede
              </div>
              <div className="card__body">
                <AssertionSupersedePanel
                  key={detail.id}
                  suggestions={supersedeSuggestions}
                  search={searchSuccessors}
                  onSupersede={handleSupersede}
                />
              </div>
            </section>
          )}

          <section className="card">
            <div className="card__header">Related assertions</div>
            <div className="card__body">
              {related.length === 0 ? (
                <p className="muted">No related or duplicate assertions found.</p>
              ) : (
                <ul className="adp-related-list">
                  {related.map((match) => (
                    <li key={match.assertion_id} className="adp-related">
                      <Link
                        to={`/assertions/${match.assertion_id}`}
                        className="adp-related-link"
                      >
                        {match.proposition ?? "Open the related assertion"}
                      </Link>
                      <div className="adp-related-meta">
                        <span className="adp-related-kind">
                          {MATCH_KIND_LABEL[match.match_kind] ?? labelize(match.match_kind)}
                        </span>
                        {match.status && (
                          <span className={`badge badge--${match.status}`}>
                            {labelize(match.status)}
                          </span>
                        )}
                        <span className="muted adp-related-score">
                          score {match.score.toFixed(2)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {related.total !== undefined && related.total > related.length && (
                <p className="muted adp-related-more">
                  {`Showing the ${related.length} strongest of ${related.total} matches.`}
                </p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

/** One revision's ratings and rationales, loaded on demand under Activity
 * (ratings stay with the revision they were given on, ruling R5). */
function RevisionRatings({
  assertionId,
  revision,
  currentUserId,
  nameFor,
  version,
}: {
  assertionId: string;
  revision: number;
  currentUserId: string;
  nameFor: (userId: string) => string;
  /**
   * The current revision only: changes whenever the page re-read this
   * revision's ratings (after the user rates, and on every reload). Once
   * loaded, the panel then reads them again, so it agrees with the Ratings
   * card (review fe-review-detail:7).
   */
  version?: number;
}) {
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [ratings, setRatings] = useState<Rating[] | null>([]);
  const [loadingRatings, setLoadingRatings] = useState(false);
  const [error, setError] = useState("");
  // Whether the user asked for these ratings, and the newest request: an
  // older answer that lands later is dropped.
  const requested = useRef(false);
  const latestRequest = useRef(0);
  const load = async () => {
    requested.current = true;
    const request = ++latestRequest.current;
    setLoadingRatings(true);
    try {
      const [sum, rows] = await Promise.all([
        api.ratingSummary(assertionId, revision),
        api.listRatings(assertionId, revision).catch(() => null),
      ]);
      if (request !== latestRequest.current) return;
      setSummary(sum);
      setRatings(rows);
      setError("");
    } catch (e) {
      if (request !== latestRequest.current) return;
      // Ratings shown earlier may no longer hold: show the error and the
      // button instead.
      setSummary(null);
      setRatings([]);
      setError(e instanceof Error ? e.message : "Unable to load ratings");
    } finally {
      if (request === latestRequest.current) setLoadingRatings(false);
    }
  };
  const seenVersion = useRef(version);
  useEffect(() => {
    if (seenVersion.current === version) return;
    seenVersion.current = version;
    if (version !== undefined && requested.current) void load();
    // load reads this render's props, which `version` changed with.
  }, [version]);
  return (
    <div className="adp-revision-ratings">
      {summary ? (
        <>
          <AssertionRatingDistribution summary={summary} modelConfidence={null} detailed />
          <AssertionRatingRationales
            ratings={ratings}
            ratingCount={summary.count}
            rationaleCount={summary.rationale_count}
            currentUserId={currentUserId}
            nameFor={nameFor}
            formatDate={fmtDate}
          />
        </>
      ) : (
        <button
          type="button"
          className="btn btn--secondary btn--sm"
          disabled={loadingRatings}
          onClick={() => void load()}
        >
          Load ratings for revision {revision}
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
