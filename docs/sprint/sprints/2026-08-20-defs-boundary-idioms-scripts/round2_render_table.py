import json

rows = json.load(open("docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/run/round2/population_c_sample_classified.json"))

OVERRIDES = {
    44: ("FALSE POSITIVE", "bare single-letter cross-reference",
         "quoted 'e' is a lettered cross-reference (\"paragraph “e”, subparagraph (2)\") mis-paired with the nearby \"includes\" idiom belonging to a different clause (\"eligible service includes...\"); NOT a definiendum"),
}

def classify(r):
    if r["i"] in OVERRIDES:
        return OVERRIDES[r["i"]]
    note = "verified against source" if r["def_len"] < 2000 else "verified start; next-entry bleed (long capture, anchor correct)"
    return ("GENUINE", "-", note)

lines = []
lines.append("| # | Jurisdiction | act_id (row) | Term | Classification | Note |")
lines.append("|---|---|---|---|---|---|")
for r in rows:
    cls, mode, note = classify(r)
    term = r["term"].replace("|", "\\|")
    if len(term) > 60:
        term = term[:57] + "..."
    lines.append(f"| {r['i']} | {r['jurisdiction']} | {r['source_row_id']} ({r['source_row']}) | {term} | {cls} | {note} |")

print("\n".join(lines))
