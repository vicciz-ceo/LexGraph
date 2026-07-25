# Sprint log — 2026-07-25-collaborative-assertions

Append-only overflow sink. Never auto-loaded; the contract points here.

## Acceptance gates (manager-defined, director-correctable)

Plain-language pass/fail conditions. The Planner turns each into failing
tests across the pyramid; QA re-verifies each independently at the end.

- G1 Draft creation: a signed-in contributor can create a draft assertion scoped to a repository + matter, and attach one or more exact documentary source spans as evidence with explicit roles (supports/contradicts/qualifies/…).
- G2 Submission: the contributor can submit the draft for review; it is visibly marked user-suggested and draft/proposed — it never appears as accepted merely from submission or high ratings.
- G3 Ratings: a second authorized user can rate the assertion revision 1–5 with an optional written rationale, and later update or remove that rating; one current rating per user per revision; every rating mutation is audited.
- G4 Aggregates: the assertion shows count, arithmetic mean (unrounded in storage), median, and 1–5 distribution — displayed separately from model confidence, review status, and evidence status; no aggregate is computed or shown with zero ratings; aggregates never change review status, confidence, or evidence status.
- G5 Review: a reviewer sees proposition, evidence (supporting and contradicting), ratings + rationales, comments, and full history, and can accept / reject / dispute / request revision; unsupported assertions cannot be accepted without recorded justification; reviewer decisions never erase user ratings.
- G6 Revisions: a material edit creates a new revision; the original stays available; editing an accepted assertion yields a new proposed revision, not a silent change; review decisions record which revision was reviewed; ratings stay attached to the revision that was rated and never auto-copy forward.
- G7 Graph: only accepted assertions appear as accepted relationships in the default graph view; proposed/disputed/rejected/superseded appear only in an opt-in "show unreviewed" mode with distinct states; rating aggregates in the graph are rebuildable projections, never authoritative.
- G8 Permissions + audit: every assertion, rating, comment, evidence, and review mutation is permission-checked server-side (viewer/contributor/reviewer/admin) and produces an audit event with actor, timestamp, matter, assertion, revision, before/after where relevant, and a correlation id; no full-document content in routine audit logs.
- G9 Matter isolation: a user without matter access cannot view, rate, comment on, or attach evidence to an assertion; evidence from an inaccessible matter cannot be attached; aggregates never mix matters — proven by automated tests.
- G10 Hostile input: raw HTML/scripts in propositions, rationales, and comments are stored/rendered as inert data; prompt-injection text inside a suggested assertion is treated as data, never as instructions; propositions are stored exactly as authored.
- G11 UI: assertion cards and a detail workspace exist with an accessible 1–5 rating widget (keyboard + screen-reader), separate "your rating" vs "team rating" displays, evidence/ratings/discussion/revision-history views, a suggest-assertion form (from selected text and from graph entities), and a reviewer panel — with explanatory text that ratings are individual opinions, not legal conclusions.
- G12 End-to-end: the 10-step contributor→rater→reviewer flow (spec §18) passes against the real API: suggest from highlighted text → second user rates 4 → summary updates → reviewer inspects → accept/reject → history preserved → accepted assertion visible in graph with evidence.

## Phase log

- 2026-07-25T20:02Z — Manager (Fable 5): repo bootstrapped, private GitHub remote created (vicciz-ceo/LexGraph), sprint state initialized, gates defined. Director gave a broad implement-the-spec mandate; gates presented in the kickoff report rather than blocking on confirmation (autonomous session). Stack ruling R1 recorded — director may override; re-planning trigger.

## Agent roster

(role → agentId, appended at every spawn)
- 2026-07-25T20:05Z — planner → ab341a135505f0cb8 (sonnet, high)
