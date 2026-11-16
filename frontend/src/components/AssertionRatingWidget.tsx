import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, ReactElement } from "react";

import { STRENGTH_LABELS, STRENGTH_VALUES } from "../constants/ratings";

// UI1 — accessible 1-5 assertion strength rating widget (spec §4 labels,
// §5 interface requirements). Types are intentionally local to this file
// (sprint ruling R7); the strength labels are shared with the distribution
// and the rationale list (src/constants/ratings.ts).

export interface AssertionRatingWidgetSaveData {
  strength: number;
  rationale: string;
}

export interface AssertionRatingWidgetProps {
  currentUserRating: number | null;
  currentRationale?: string | null;
  onSave: (data: AssertionRatingWidgetSaveData) => void | Promise<void>;
  onRemove: () => void | Promise<void>;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function AssertionRatingWidget({
  currentUserRating,
  currentRationale = "",
  onSave,
  onRemove,
}: AssertionRatingWidgetProps): ReactElement {
  const [selectedStrength, setSelectedStrength] = useState<number | null>(currentUserRating);
  const [rationale, setRationale] = useState(currentRationale ?? "");
  const [focusedIndex, setFocusedIndex] = useState(
    currentUserRating != null ? currentUserRating - 1 : 0
  );
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const rationaleId = useId();
  useEffect(() => {
    setSelectedStrength(currentUserRating);
    setRationale(currentRationale ?? "");
  }, [currentUserRating, currentRationale]);

  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const hasExistingRating = currentUserRating != null;

  const moveFocus = (nextIndex: number) => {
    const clamped = Math.max(0, Math.min(STRENGTH_VALUES.length - 1, nextIndex));
    setFocusedIndex(clamped);
    buttonRefs.current[clamped]?.focus();
  };

  const handleGroupKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        moveFocus(focusedIndex + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        moveFocus(focusedIndex - 1);
        break;
      case "Home":
        event.preventDefault();
        moveFocus(0);
        break;
      case "End":
        event.preventDefault();
        moveFocus(STRENGTH_VALUES.length - 1);
        break;
      default:
        break;
    }
  };

  const selectValue = (value: number, index: number) => {
    setSelectedStrength(value);
    setFocusedIndex(index);
    setStatus("idle");
    setFeedbackMessage(null);
  };

  const handleSave = async () => {
    if (selectedStrength == null) {
      return;
    }
    setStatus("saving");
    setFeedbackMessage(null);
    try {
      await onSave({ strength: selectedStrength, rationale });
      setStatus("saved");
      setFeedbackMessage(
        hasExistingRating ? "Rating updated." : "Rating saved."
      );
    } catch (error) {
      setStatus("error");
      setFeedbackMessage(
        error instanceof Error
          ? `Failed to save rating: ${error.message}`
          : "Failed to save rating due to an unexpected error."
      );
    }
  };

  const handleRemove = async () => {
    setStatus("saving");
    setFeedbackMessage(null);
    try {
      await onRemove();
      setSelectedStrength(null);
      setRationale("");
      setStatus("saved");
      setFeedbackMessage("Rating removed.");
    } catch (error) {
      setStatus("error");
      setFeedbackMessage(
        error instanceof Error
          ? `Failed to remove rating: ${error.message}`
          : "Failed to remove rating due to an unexpected error."
      );
    }
  };

  return (
    <div className="assertion-rating-widget">
      <div
        className="assertion-rating-widget__options"
        role="radiogroup"
        aria-label="Rate the strength of this assertion, from 1 (very weak) to 5 (very strong)"
        onKeyDown={handleGroupKeyDown}
      >
        {STRENGTH_VALUES.map((value, index) => {
          const isSelected = selectedStrength === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-label={`${value} - ${STRENGTH_LABELS[value]}`}
              tabIndex={focusedIndex === index ? 0 : -1}
              ref={(element) => {
                buttonRefs.current[index] = element;
              }}
              className={
                isSelected
                  ? "assertion-rating-widget__option assertion-rating-widget__option--selected"
                  : "assertion-rating-widget__option"
              }
              onClick={() => selectValue(value, index)}
            >
              <span className="assertion-rating-widget__option-number" aria-hidden="true">
                {value}
              </span>
              <span className="assertion-rating-widget__option-text" aria-hidden="true">
                {STRENGTH_LABELS[value]}
              </span>
            </button>
          );
        })}
      </div>

      <div className="assertion-rating-widget__rationale">
        <label htmlFor={rationaleId}>Rationale (optional)</label>
        <textarea
          id={rationaleId}
          value={rationale}
          onChange={(event) => setRationale(event.target.value)}
        />
      </div>

      <div className="assertion-rating-widget__actions">
        <button type="button" onClick={handleSave} disabled={status === "saving" || selectedStrength == null}>
          {hasExistingRating ? "Update rating" : "Save rating"}
        </button>
        {hasExistingRating && (
          <button type="button" onClick={handleRemove} disabled={status === "saving"}>
            Remove rating
          </button>
        )}
      </div>

      {feedbackMessage && (
        <p role={status === "error" ? "alert" : "status"}>{feedbackMessage}</p>
      )}
    </div>
  );
}
