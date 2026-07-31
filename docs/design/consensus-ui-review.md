# Consensus UI — design review and implementation notes

**Source:** `stitch_consensus_knowledge_verification_platform.zip` (Stitch-generated
design, 10 screens + [DESIGN.md](consensus-ui/DESIGN.md)). The design describes a
generic "enterprise consensus / knowledge verification" product; this document
records what could not work as designed against the real LexGraph backend, and
the resolution implemented for each. The result is the application shell under
`frontend/src/` (app foundation + one page per screen).

## Verdict

The design's information architecture (sidebar workspace nav, review queue,
knowledge base, suggest flow, contested queue, profile, analytics, admin) maps
cleanly onto LexGraph's collaborative-assertion feature set and was implemented
faithfully. Its *semantics*, however, assumed a voting product; every screen
needed corrections to be truthful to LexGraph's domain rules, and the design
carried structural problems (CDN dependencies, fabricated data, missing matter
scoping) that had to be fixed for a fork-and-run open-source repo.

## Cross-cutting problems and resolutions

| # | Problem in the design | Resolution implemented |
|---|---|---|
| 1 | **Votes don't exist.** Accept/decline tallies, quorums ("5 of 7 votes"), "Cast Vote" buttons, and "your grades weight the final confidence score" imply member voting decides outcomes. LexGraph separates three things by spec: per-user 1–5 *strength ratings* (never change status), *reviewer decisions* (accept/reject/dispute/request-revision, role-gated), and *model confidence* (0–1, read-only). | All vote UI became rating UI (1–5 strength + rationale, per revision, via the ratings API). Review actions render only for `reviewer`/`admin` roles and call the review endpoints. Quorum widgets became rating summaries (count/average/median/distribution). Copy states explicitly that ratings inform but never decide. |
| 2 | **"Reviewer Confidence" conflated with model confidence.** The queue's 1–5 widget and the analytics "Avg. Confidence 4.2/5.0" mixed user ratings with the model's 0–1 confidence. | Ratings are always labeled "strength rating (1–5)"; model confidence is always a separate percentage chip shown only on `model_suggested` assertions. Never merged into one indicator (spec §5). |
| 3 | **No matter context.** Every backend query requires `matter_id`; the design had no notion of matters and no way to discover them (the API had no listing endpoint either). | New backend workspace surface: `GET /api/v1/me` (identity + matter memberships with roles) and a matter selector in the sidebar. All pages read the active matter from the session. |
| 4 | **Sign-in screen was fiction.** SSO button and username/password form, with the full authenticated chrome (nav, search, notifications) rendered *around* the sign-in card. | The backend's auth seam is `Authorization: Bearer <user_id>` (no IdP, no passwords). The page is now a bare centered card (no chrome) with a single User ID field, validated against `GET /me`; the seeded demo logins are offered as one-click chips. SSO/password removed rather than faked. |
| 5 | **CDN/runtime dependencies.** Tailwind CDN script, Google Fonts (Inter), Material Symbols webfont, and `lh3.googleusercontent.com` images (logo, stock avatars) — none acceptable for an offline-capable OSS build. | Design tokens compiled to CSS custom properties (`src/styles/tokens.css`, values from DESIGN.md's frontmatter); Inter self-hosted via `@fontsource-variable/inter`; icons are bundled inline SVGs (`src/app/icons.tsx`); logo is an inline mark; avatars are initials chips (no avatar data exists in the model). |
| 6 | **Fabricated identity/metadata.** Job titles ("Sales Ops"), departments (Logistics/HR/Architecture), headshots, "GPT-4 Pipeline v4.2.1" provenance, "System Integrity Validated" badges, hashtag taxonomies. | Users render as `display_name` + email + initials chip (the real model). Departments became real dimensions (`assertion_type`, `jurisdiction`). Model provenance renders the real `origin` + `confidence` fields. Decorative fictions dropped. |
| 7 | **Inconsistent chrome.** 8 of 10 screens hardcoded "Review Queue" as active nav; two screens had a different 7-item sidebar; origin-chip and button recipes varied per screen. | One canonical `AppShell` (route-driven active state, role-gated Admin item) and one primitive set (`.btn`, `.chip`, `.badge`, `.card`, `.table`, `.filter-bar`) in `src/styles/app.css`, following the audit's canonical recipes. |

### Design-system conflicts resolved

DESIGN.md's frontmatter palette (used by the actual screens: primary `#00685f`,
blue `#0058be`, violet `#6b38d4`, blue-tinted surfaces) contradicts its own
prose ("teal-600 #0d9488", slate surfaces). **The frontmatter/screens palette
wins** — it is what the design actually renders. Two prose rules were kept
where the screens were incoherent: the traffic-light status colors (green
accepted / red rejected / amber pending — the screens had no amber token and
sometimes used teal for accepted) and WCAG-AA text contrast on tinted chips.
The Stitch config remaps Tailwind radius names (`rounded-full` = 12px, not a
pill); tokens.css encodes the rendered look (12px soft-pill chips, 8px cards,
4px buttons/inputs).

## Backend additions the design exposed

The design assumed capabilities the API did not have. Added (additively, in
`backend/app/routers/workspace.py`, tests in
`backend/tests/integration/test_workspace.py`):

- `GET /api/v1/me` — caller identity + matter memberships/roles (powers
  sign-in, the matter selector, and role-gated UI).
- `GET /api/v1/matters/{id}/members` — member roster (any member).
- `POST/PUT/DELETE /api/v1/matters/{id}/members[/{user_id}]` — admin-gated role
  management with a "matter keeps ≥1 admin" lockout guard (powers the Admin
  console).
- `python -m app.seed_demo` — seeds a demo workspace (org/repo/matters, four
  role-named users, documents/spans, assertions across every status with
  ratings/comments/evidence) so a fork runs the full UI immediately.

## Screen-by-screen

- **sign_in** → `SignInPage`. Chrome stripped; single User ID field + demo
  account chips; validates via `GET /me`; errors surface inline. SSO, password
  field, and fake on-prem/policy badges removed.
- **review_queue_1 + 2** (two divergent designs of the same route) →
  `ReviewQueuePage`, merged: queue_1's layout (header count chip, filter
  pills, guidelines rail) + queue_2's richer card internals, with rating
  summaries instead of vote tallies. Pending count = `status=proposed` total.
  Review actions role-gated; "Decline" renamed Reject; dispute/request-revision
  included; unsupported-evidence acceptances require a justification (spec
  behavior the design lacked).
- **assertion_detail** → `AssertionDetailPage`. Single `GET /assertions/{id}`
  (embeds evidence/comments/revisions/summary) + related matches. "Vote panel"
  split into rating widget (all members with `assertion:rate`) and reviewer
  panel (role-gated). "AI Reasoning" box became honest model provenance
  (origin, confidence %, raw vs. sanitized proposition). Quorum ring became
  rating distribution.
- **suggest_assertion** → `SuggestAssertionPage`. Free-text-only form gained
  the required fields the design omitted (`assertion_type`, subject/object
  entities) via the existing `AssertionSuggestionForm`; evidence is staged
  client-side as source-span references then attached after creation; the
  fictional Domain select and file upload were dropped. Duplicate warnings come
  from the create response's `similar_assertions`.
- **knowledge_base** → `KnowledgeBasePage`. Accepted-assertion table with real
  search/filter/sort; "Votes" column renamed Ratings (avg + count + standing);
  CSV export computed client-side; nav active-state bug fixed.
- **contested_queue_adjudication** → `ContestedPage`. `status=disputed` queue;
  "Consensus Split" became rating-strength distribution; departments dropped;
  "Flags" became the real `evidence_status`; adjudication actions are the
  review endpoints, role-gated.
- **admin_console** → `AdminPage`. Users & Roles works against the new members
  API with the real role vocabulary (viewer/contributor/reviewer/admin,
  per-matter); "Voting Rules" became a read-only Review Policy explainer;
  the global audit-log tab was dropped (audit exists per-assertion via
  `/history`, surfaced on the detail page).
- **my_profile_activity** → `ProfilePage`. Stats computed from real queries
  (authored counts, acceptance rate, awaiting-my-rating via
  `unrated_by_me=true`); thumbs became rating shortcuts; expertise/weighting
  chips removed ("ratings never gain weight" is a domain rule); Agreement %
  became suggestion-acceptance %.
- **analytics_dashboard** → `AnalyticsPage`. Matter-scoped, computed
  client-side from the assertions list (no fake platform metrics): status
  mix, acceptance rate by origin and by assertion type, strength vs. model
  confidence (kept separate), top contributors from real members.

## Known limitations (deliberate)

- Evidence rows reference `source_span_id`s; there is no span-resolution
  endpoint yet, so evidence lists show ids + roles, not quote text.
- Notifications remain in-process (existing platform limitation).
- The sign-in seam is the documented test-token scheme; a real IdP is a
  deployment concern, out of scope here.
- Analytics aggregates are computed client-side from the matter's assertion
  list; fine at demo/matter scale, a stats endpoint would be the next step.
