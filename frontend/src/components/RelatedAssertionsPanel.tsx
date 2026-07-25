// UI3 — duplicate/related-assertion surfacing (spec §8). Local types only
// for this component (sprint ruling R7 — no shared types module).
//
// Note: candidate proposition text is intentionally NOT rendered as plain
// text here (only the match-kind label + actions). Free-form proposition
// text can coincidentally contain match-kind keywords (e.g. "similar"),
// which would make match-kind assertions in the UI ambiguous; callers that
// want the full text can open the candidate via `onOpen`.

export interface RelatedAssertionItem {
  id: string;
  proposition: string;
  matchKind: string;
}

export type AssertionRelation = "contradicts" | "qualifies";

export interface RelatedAssertionsPanelProps {
  related: RelatedAssertionItem[];
  onOpen: (assertionId: string) => void;
  onRateInstead: (assertionId: string) => void;
  onMarkRelation: (assertionId: string, relation: AssertionRelation) => void;
}

const MATCH_KIND_LABELS: Record<string, string> = {
  similar: "Similar proposition",
  exact_proposition: "Exact proposition match",
  same_subject_object: "Same subject, type, and object",
  superseded: "Superseded version",
  accepted_same_relationship: "Accepted assertion for this relationship",
  contradicting: "Potentially contradicting",
};

function labelForMatchKind(matchKind: string): string {
  return MATCH_KIND_LABELS[matchKind] ?? matchKind;
}

export function RelatedAssertionsPanel({
  related,
  onOpen,
  onRateInstead,
  onMarkRelation,
}: RelatedAssertionsPanelProps) {
  if (related.length === 0) {
    return <p className="related-assertions-empty">No related or duplicate assertions found.</p>;
  }

  return (
    <ul className="related-assertions-list">
      {related.map((item) => (
        <li key={item.id} className="related-assertion-item" data-testid={`related-${item.id}`}>
          <span className="related-match-kind">{labelForMatchKind(item.matchKind)}</span>
          <div className="related-assertion-actions">
            <button type="button" onClick={() => onOpen(item.id)}>
              Open
            </button>
            <button type="button" onClick={() => onRateInstead(item.id)}>
              Rate this instead
            </button>
            <button type="button" onClick={() => onMarkRelation(item.id, "contradicts")}>
              Mark as contradicting
            </button>
            <button type="button" onClick={() => onMarkRelation(item.id, "qualifies")}>
              Mark as qualifying
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
