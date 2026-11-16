// API response shapes, mirrored field-for-field from the backend
// serializers (backend/app/routers/*.py). Wire format stays snake_case;
// pages adapt to component-local prop shapes at the call site.

export type AssertionStatus =
  | "draft"
  | "proposed"
  | "revision_requested"
  | "accepted"
  | "rejected"
  | "disputed"
  | "superseded"
  | "withdrawn";

export type AssertionOrigin = "user_suggested" | "model_suggested" | "system_generated";

export type EvidenceStatus = "evidenced" | "unsupported" | "awaiting_evidence";

export interface EntityRef {
  type: string | null;
  id: string | null;
}

export interface Assertion {
  id: string;
  organization_id: string;
  repository_id: string;
  matter_id: string;
  assertion_type: string;
  proposition: string;
  proposition_raw: string | null;
  subject_entity: EntityRef;
  object_entity: EntityRef | null;
  origin: AssertionOrigin;
  status: AssertionStatus;
  /** Derived read-time grade: proposed | weak | probable | strong, or the
   * status passthrough for non-proposed assertions. */
  standing: string;
  author_user_id: string;
  agent_provenance?: { platform: string; model?: string | null; run_id?: string | null } | null;
  confidence: number | null;
  jurisdiction: string | null;
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  superseded_by_assertion_id: string | null;
  current_revision_number: number | null;
  evidence_status: EvidenceStatus;
}

/** Current-revision rating aggregate embedded in every GET /assertions item:
 * all ratings, the author's included. Null when the revision is unrated or
 * the assertion has no revision row (definition-link pipeline output). */
export interface ListRatingsSummary {
  assertion_id: string;
  assertion_revision_id: string;
  average: number;
  median: number;
  count: number;
  distribution: Record<string, number>;
}

/** A GET /assertions item: the detail serializer's fields plus list-only ones
 * (optional here so fixtures built from a plain Assertion still type-check). */
export interface AssertionListItem extends Assertion {
  ratings_summary?: ListRatingsSummary | null;
  current_user_rating?: CurrentUserRating | null;
  /** UTC instant: the later of updated_at and the newest audit event. */
  last_activity_at?: string;
}

export interface AssertionList {
  items: AssertionListItem[];
  /** Every match, whatever limit/offset returned. */
  total: number;
  /** The request's page size; null when it set none (every match returned). */
  limit?: number | null;
  offset?: number;
}

export interface AssertionListParams {
  q?: string;
  origin?: AssertionOrigin;
  status?: AssertionStatus;
  evidence_status?: EvidenceStatus;
  jurisdiction?: string;
  min_average_rating?: number;
  min_rating_count?: number;
  unrated_by_me?: boolean;
  my_rating?: number;
  /** Comma-separated sort keys; a "-" prefix sorts descending. */
  sort?: string;
  assertion_type?: string;
  author_user_id?: string;
  subject_entity_type?: string;
  subject_entity_id?: string;
  object_entity_type?: string;
  object_entity_id?: string;
  /** ISO instants; each range is half-open, [from, to). */
  created_from?: string;
  created_to?: string;
  last_activity_from?: string;
  last_activity_to?: string;
  /** YYYY-MM-DD: in effect on that date. */
  effective_on?: string;
  /** Page size, 1–500. Without it every match is returned. */
  limit?: number;
  offset?: number;
}

/** GET /matters/{id}/assertion-stats takes the list filters except q, sort,
 * limit and offset, plus creation-count bucket edges. */
export interface AssertionStatsParams
  extends Omit<AssertionListParams, "q" | "sort" | "limit" | "offset"> {
  /** Comma-separated, strictly increasing ISO instants (2–101): N edges give
   * N − 1 half-open buckets. */
  created_bucket_edges?: string;
}

/** Matter-level aggregates over every assertion matching the filters. */
export interface AssertionStats {
  matter_id: string;
  total: number;
  by_status: Partial<Record<AssertionStatus, number>>;
  by_origin: Partial<Record<AssertionOrigin, number>>;
  by_origin_status: Partial<Record<AssertionOrigin, Partial<Record<AssertionStatus, number>>>>;
  by_type: Record<string, number>;
  by_evidence_status: Partial<Record<EvidenceStatus, number>>;
  /** Every author, by total descending, then user id. */
  authors: {
    user_id: string;
    total: number;
    by_status: Partial<Record<AssertionStatus, number>>;
  }[];
  /** Mean model confidence per origin, over assertions that carry one. */
  confidence_by_origin: Partial<Record<AssertionOrigin, { count: number; average: number }>>;
  /** Current-revision ratings: rated assertions, ratings, mean of their averages. */
  ratings: { rated_assertions: number; ratings: number; average_of_averages: number | null };
  created_buckets: { start: string; end: string; count: number }[];
}

export interface Evidence {
  quote_text?: string | null;
  document_title?: string | null;
  id: string;
  assertion_id: string;
  source_span_id: string;
  evidence_role: string;
  added_by_user_id: string;
  created_at: string;
}

export interface Revision {
  id: string;
  assertion_id: string;
  revision_number: number;
  proposition: string;
  proposition_raw: string | null;
  assertion_type: string;
  subject_entity: EntityRef;
  object_entity: EntityRef | null;
  jurisdiction: string | null;
  effective_from: string | null;
  effective_to: string | null;
  revision_reason: string | null;
  edited_by_user_id: string;
  created_at: string;
}

export interface AssertionComment {
  id: string;
  assertion_id: string;
  user_id: string;
  parent_comment_id: string | null;
  comment_text: string;
  comment_text_raw: string | null;
  created_at: string;
  updated_at: string | null;
  deleted_at: string | null;
}

export interface HistoryEvent {
  id: string;
  event_type: string;
  actor_user_id: string;
  timestamp: string;
  assertion_revision_number: number | null;
  previous_value: string | null;
  new_value: string | null;
  correlation_id: string | null;
}

export interface CurrentUserRating {
  strength: number;
  rationale: string | null;
  updated_at: string | null;
}

export interface RatingSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
  assertion_id: string;
  assertion_revision_id: string;
  current_user_rating: CurrentUserRating | null;
  rationale_count: number;
}

export interface Rating {
  id: string;
  assertion_id: string;
  assertion_revision_id: string;
  user_id: string;
  strength: number;
  rationale: string | null;
  rationale_raw: string | null;
  created_at: string;
  updated_at: string | null;
}

/** GET /assertions/{id} embeds the full working set for the detail page. */
export interface AssertionDetail extends Assertion {
  evidence: Evidence[];
  ratings_summary: {
    assertion_id: string;
    assertion_revision_id: string | null;
    average: number;
    median: number;
    count: number;
    distribution: Record<string, number>;
  } | null;
  comments: AssertionComment[];
  revision_history: Revision[];
}

export interface RelatedMatch {
  assertion_id: string;
  match_kind: "exact_proposition" | "same_subject_type_object" | "similar" | string;
  score: number;
}

export interface AppNotification {
  id: string;
  event_type: string;
  actor_user_id: string;
  recipient_user_id: string;
  payload: Record<string, unknown>;
  created_at: string;
  read: boolean;
  /** The assertion the notice is about (also in payload.assertion_id). */
  assertion_id?: string | null;
  matter_id?: string | null;
  /** App route of that assertion ("/assertions/<id>"); null once the
   * recipient can no longer open it. */
  link?: string | null;
  /** Read-time context; null once the recipient left the matter. */
  context?: NotificationContext | null;
  read_at?: string | null;
}

export interface NotificationContext {
  proposition: string | null;
  assertion_status: AssertionStatus | null;
  assertion_origin: AssertionOrigin | null;
  matter_name: string | null;
  actor_display_name: string | null;
}

export interface NotificationListParams {
  limit?: number;
  offset?: number;
  unread_only?: boolean;
}

export interface NotificationPreference {
  event_type: string;
  enabled: boolean;
  default: boolean;
}

export interface GraphEdge {
  assertion_id: string;
  review_state: AssertionStatus;
  subject_entity_id: string | null;
  subject_entity_type: string | null;
  object_entity_id: string | null;
  object_entity_type: string | null;
  rating_aggregate: {
    count: number;
    mean: number | null;
    median: number | null;
    distribution: Record<string, number>;
  };
  evidence_count: number;
}

export interface MatterGraph {
  matter_id: string;
  edges: GraphEdge[];
  /** Every edge of the view; `edges` holds at most `limit` (default 1000) after `offset`. */
  total?: number;
  limit?: number;
  offset?: number;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
}

/** How an account signs in (backend/app/routers/users.py): `active` = a
 * generated sign-in token; `legacy` = the token is still the account's
 * public user id (left by the upgrade migration; rotate it); `none` = no
 * sign-in credential. */
export type SignInStatus = "active" | "legacy" | "none";

/** GET /users row (admin console). Never carries a token or its hash. */
export interface UserAccount extends UserInfo {
  sign_in_status: SignInStatus;
}

/** POST /users and POST /users/{id}/sign-in-token: the account plus its
 * new sign-in token, which the API returns exactly once. */
export interface IssuedSignIn extends UserAccount {
  sign_in_token: string;
}

export type MatterRoleName = "viewer" | "contributor" | "reviewer" | "admin";

export interface MatterMembership {
  id: string;
  name: string;
  repository_id: string;
  organization_id: string;
  role: MatterRoleName;
}

export interface Me {
  user: UserInfo;
  matters: MatterMembership[];
}

export interface MatterMember {
  user: UserInfo;
  role: MatterRoleName;
}
