import { useState } from "react";
import type { ReactElement } from "react";

// UI2 — evidence selector (spec §6). Lists attached evidence spans with
// their supporting/contradicting role, lets the user add or remove
// spans, search for source spans to attach, and flag that further
// evidence is still needed. Types are local to this file (sprint ruling
// R7) — no shared types module this sprint.

export type EvidenceRole = "supports" | "contradicts";

export interface AssertionEvidenceItem {
  id: string;
  sourceSpanId: string;
  evidenceRole: EvidenceRole;
  quote: string;
}

export interface NewEvidenceInput {
  sourceSpanId: string;
  evidenceRole: EvidenceRole;
  quote: string;
}

export interface AssertionEvidenceSelectorProps {
  evidence: AssertionEvidenceItem[];
  onAdd: (input: NewEvidenceInput) => void;
  onRemove: (evidenceId: string) => void;
  needsFurtherEvidence?: boolean;
  onNeedsFurtherEvidenceChange?: (value: boolean) => void;
}

function humanizeRole(role: EvidenceRole): string {
  return role === "supports" ? "Supports" : "Contradicts";
}

export function AssertionEvidenceSelector({
  evidence,
  onAdd,
  onRemove,
  needsFurtherEvidence = false,
  onNeedsFurtherEvidenceChange,
}: AssertionEvidenceSelectorProps): ReactElement {
  const [searchTerm, setSearchTerm] = useState("");
  const [furtherEvidenceNeeded, setFurtherEvidenceNeeded] = useState(needsFurtherEvidence);

  const handleAdd = (role: EvidenceRole) => {
    onAdd({
      sourceSpanId: searchTerm.trim() ? `search:${searchTerm.trim()}` : "",
      evidenceRole: role,
      quote: searchTerm.trim(),
    });
  };

  const handleFurtherEvidenceToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.checked;
    setFurtherEvidenceNeeded(value);
    onNeedsFurtherEvidenceChange?.(value);
  };

  return (
    <div className="assertion-evidence-selector">
      <h3>Evidence</h3>

      <ul className="assertion-evidence-selector__list">
        {evidence.map((item) => (
          <li key={item.id} className="assertion-evidence-selector__item">
            <span className="assertion-evidence-selector__role">{humanizeRole(item.evidenceRole)}</span>
            <span className="assertion-evidence-selector__quote">{item.quote}</span>
            <button type="button" onClick={() => onRemove(item.id)}>
              Remove
            </button>
          </li>
        ))}
      </ul>

      <div className="assertion-evidence-selector__search">
        <label htmlFor="evidence-search">Search for source spans</label>
        <input
          id="evidence-search"
          type="text"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
        />
      </div>

      <div className="assertion-evidence-selector__actions">
        <button type="button" onClick={() => handleAdd("supports")}>
          Add supporting evidence
        </button>
        <button type="button" onClick={() => handleAdd("contradicts")}>
          Add contradicting evidence
        </button>
      </div>

      <div className="assertion-evidence-selector__further-evidence">
        <label htmlFor="evidence-further-needed">Further evidence needed</label>
        <input
          id="evidence-further-needed"
          type="checkbox"
          checked={furtherEvidenceNeeded}
          onChange={handleFurtherEvidenceToggle}
        />
      </div>
    </div>
  );
}
