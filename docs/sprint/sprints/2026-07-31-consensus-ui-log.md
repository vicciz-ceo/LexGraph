# Sprint log — 2026-07-31-consensus-ui (append-only; not auto-loaded)

## Agent roster

- Screen-analysis workflow: wf_f461bba1-69a (11 agents, complete)
- Developer pass workflow (UI1–UI9): wf_dfea95a4-a7c (9 agents, complete)
- Planner (qa-fail RED tests, walkthrough defects): ae0bfd6870363ab18

## Manager live walkthrough (G1) — 2026-07-31, seeded dev.db, vite :5173 + uvicorn :8000

Verified working end-to-end against the real backend:
- Sign-in card (bare chrome, demo chips, single User ID field); programmatic
  submit → /me → session. NOTE: the in-app browser pane's synthesized clicks
  did not reach React (pane quirk — form worked via real DOM events and via
  the agent's own live test); not an app defect.
- Reviewer (riva): queue shows 4 proposed w/ origin chips, standing badges
  (weak 1.5/5, strong 4.0/5), separate model-confidence chips; Accept on
  evidenced item → 201, count 4→3, list refreshed; detail page full render
  (proposition, entities, evidence w/ span ids, comments, revision activity,
  team rating distribution + median, own-rating preload); rating update 4→5
  → verified via ratings summary API (avg 4.0, distribution {3:1,5:1}).
- Knowledge Base: 5 accepted (incl. live-accepted item), server-side q=
  "liability" → 1 row, "Results for" banner, ratings/`independent of review
  status` legend, Export CSV present.
- Contested: 2 disputed, rating-strength bars, red Unsupported chip; drawer
  w/ summary tiles + contradicts evidence; Accept on unsupported → guided
  justification textarea (no premature API call) → Confirm accept →
  status=accepted, reviewed_by=reviewer (API-verified).
- Contributor (caleb): Suggest form (real AssertionSuggestionForm) → filled
  subject UUID/standalone/SUPPORTS/proposition → Submit for review →
  created proposed/user_suggested/author=contributor (API-verified),
  navigated to detail. Profile: stats independently recomputed and correct
  (12 authored, 3 accepted, 75% = 3/(3+1), 4 awaiting my rating), tabs +
  matters card + notifications count.
- Viewer (vera): NO Accept/Reject buttons, NO rating radios, NO Admin nav,
  per-card "Reviewer role required to decide." note. Role gating airtight.

Defects found (routed Planner→Developer per harness):
- D1 (high): AdminPage blank crash — client.ts mistypes GET /matters/{id}/members
  as {items:[...]}; backend returns a bare array. res.items → undefined →
  members.length TypeError at render. MANAGER-AUTHORED defect (client.ts is
  baseline code); page agents coded to the type as briefed.
- D2 (medium): same root cause — author display-name resolution dead on
  ReviewQueue/Analytics ("Suggested by admin" instead of "Ada Admin");
  detail page never resolves non-self names (uses session user only).
- D3 (medium): Accept on evidence_status="awaiting_evidence" fires the API
  and surfaces the server 4xx instead of opening the pre-flight justification
  form (AssertionReviewPanel only gates on "unsupported"; backend requires
  justification for BOTH no-evidence states). Error WAS surfaced honestly
  (role=alert with backend detail); data integrity unaffected.

Environment notes: browser-pane screenshots intermittently stale/mis-scaled;
verification cross-checked via DOM reads + direct API probes throughout.
Stale localStorage from the dev-agent's session (old matter id) produced a
one-time 403 banner before storage clear — fresh-boot behavior verified
clean; not reproducible for fork users.

## Roster update
- Developer (D1–D3 fix): a2368941f27a7c9c8 (spawned after Planner RED commit 9b99ce4)
