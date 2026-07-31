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

export interface AssertionList {
  items: Assertion[];
  total: number;
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
  sort?: string;
}

export interface Evidence {
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
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
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
