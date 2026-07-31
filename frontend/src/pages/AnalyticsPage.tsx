// AnalyticsPage — matter-scoped dashboard computed entirely client-side.
//
// No analytics/stats endpoints exist, so every number here is honestly
// derived from ONE assertions fetch for the current matter, plus the
// member list (names) and a capped batch of rating summaries. The three
// platform signals stay strictly separate: user strength ratings (1–5),
// model confidence (0–1, AI-deduced only, shown as %), and review status.
// Charts are hand-rolled inline SVG driven by design tokens — no chart lib.

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import "../styles/pages/analytics.css";

import { api } from "../api/client";
import type { Assertion, RatingSummary, UserInfo } from "../api/types";
import { useActiveSession } from "../app/session";

/** Rating summaries are an N+1 fetch — bound it for dashboard use. */
const RATING_SUMMARY_CAP = 50;
const ACTIVITY_WEEKS = 8;
const TOP_TYPES = 6;
const TOP_CONTRIBUTORS = 8;

// --- Derivations -----------------------------------------------------------

const STATUS_BUCKETS = [
  { key: "accepted", label: "Accepted", fill: "ana-fill--accepted" },
  { key: "proposed", label: "Proposed", fill: "ana-fill--proposed" },
  { key: "disputed", label: "Disputed", fill: "ana-fill--disputed" },
  { key: "rejected", label: "Rejected", fill: "ana-fill--rejected" },
  { key: "other", label: "Other", fill: "ana-fill--neutral" },
] as const;

type StatusBucketKey = (typeof STATUS_BUCKETS)[number]["key"];

function bucketOf(status: Assertion["status"]): StatusBucketKey {
  if (
    status === "accepted" ||
    status === "proposed" ||
    status === "disputed" ||
    status === "rejected"
  ) {
    return status;
  }
  return "other";
}

/** Local midnight on the Monday of the given date's ISO week. */
function startOfIsoWeek(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d;
}

function weeklyBuckets(
  items: Assertion[],
  weeks: number,
): { starts: Date[]; counts: number[] } {
  const currentStart = startOfIsoWeek(new Date());
  const starts: Date[] = [];
  for (let i = weeks - 1; i >= 0; i--) {
    const d = new Date(currentStart);
    d.setDate(d.getDate() - i * 7);
    starts.push(d);
  }
  const indexByTime = new Map(starts.map((d, i) => [d.getTime(), i]));
  const counts = new Array<number>(weeks).fill(0);
  for (const item of items) {
    const created = new Date(item.created_at);
    if (Number.isNaN(created.getTime())) continue;
    const index = indexByTime.get(startOfIsoWeek(created).getTime());
    if (index !== undefined) counts[index] += 1;
  }
  return { starts, counts };
}

interface ContributorRow {
  userId: string;
  authored: number;
  accepted: number;
}

interface OriginDatum {
  key: string;
  label: string;
  accepted: number;
  rejected: number;
}

function initialsOf(name: string | undefined): string {
  if (!name) return "?";
  const letters = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  return letters || "?";
}

// --- Presentational pieces --------------------------------------------------

function KpiCard({
  id,
  label,
  value,
  caption,
}: {
  id: string;
  label: string;
  value: ReactNode;
  caption?: ReactNode;
}) {
  return (
    <div className="card ana-kpi">
      <span className="ana-kpi__label">{label}</span>
      <span className="ana-kpi__value" data-testid={`ana-kpi-${id}`}>
        {value}
      </span>
      {caption !== undefined && <span className="ana-kpi__caption">{caption}</span>}
    </div>
  );
}

function StatusMixChart({ counts }: { counts: Record<StatusBucketKey, number> }) {
  const total = STATUS_BUCKETS.reduce((sum, b) => sum + counts[b.key], 0);
  const label = `Status mix: ${STATUS_BUCKETS.map(
    (b) => `${counts[b.key]} ${b.label.toLowerCase()}`,
  ).join(", ")}`;

  let x = 0;
  const segments = STATUS_BUCKETS.map((b) => {
    const count = counts[b.key];
    if (count === 0 || total === 0) return null;
    const width = (count / total) * 100;
    const rect = (
      <rect key={b.key} x={x} y={0} width={width} height={8} className={b.fill} />
    );
    x += width;
    return rect;
  });

  return (
    <div className="ana-chart-body">
      <svg
        className="ana-stack"
        viewBox="0 0 100 8"
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <rect x={0} y={0} width={100} height={8} className="ana-fill--track" />
        {segments}
      </svg>
      <ul className="ana-legend">
        {STATUS_BUCKETS.map((b) => (
          <li key={b.key} className="ana-legend__item">
            <span className={`ana-legend__swatch ${b.fill}`} aria-hidden="true" />
            {b.label} · {counts[b.key]}
          </li>
        ))}
      </ul>
    </div>
  );
}

function OriginChart({ data }: { data: OriginDatum[] }) {
  const W = 320;
  const BASE = 112;
  const TOP = 18;
  const BAR = 34;
  const GAP = 8;
  const max = Math.max(1, ...data.flatMap((g) => [g.accepted, g.rejected]));
  const label = `Acceptance by origin. ${data
    .map((g) => `${g.label}: ${g.accepted} accepted, ${g.rejected} rejected`)
    .join(". ")}.`;

  return (
    <div className="ana-chart-body">
      <svg className="ana-origin" viewBox="0 0 320 140" role="img" aria-label={label}>
        <line x1={8} y1={BASE} x2={W - 8} y2={BASE} className="ana-origin__axis" />
        {data.map((g, i) => {
          const cx = (W / (data.length * 2)) * (2 * i + 1);
          const bars = [
            { id: "accepted", value: g.accepted, x: cx - BAR - GAP / 2, fill: "ana-fill--accepted" },
            { id: "rejected", value: g.rejected, x: cx + GAP / 2, fill: "ana-fill--rejected" },
          ];
          return (
            <g key={g.key}>
              {bars.map((bar) => {
                const height = (bar.value / max) * (BASE - TOP);
                return (
                  <g key={bar.id}>
                    <rect
                      x={bar.x}
                      y={BASE - height}
                      width={BAR}
                      height={height}
                      rx={2}
                      className={bar.fill}
                    />
                    <text
                      x={bar.x + BAR / 2}
                      y={BASE - height - 6}
                      textAnchor="middle"
                      className="ana-origin__value"
                    >
                      {bar.value}
                    </text>
                  </g>
                );
              })}
              <text x={cx} y={132} textAnchor="middle" className="ana-origin__label">
                {g.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="ana-legend">
        <li className="ana-legend__item">
          <span className="ana-legend__swatch ana-fill--accepted" aria-hidden="true" />
          Accepted
        </li>
        <li className="ana-legend__item">
          <span className="ana-legend__swatch ana-fill--rejected" aria-hidden="true" />
          Rejected
        </li>
      </ul>
    </div>
  );
}

function TypeBars({ types }: { types: [string, number][] }) {
  const max = Math.max(1, ...types.map(([, count]) => count));
  return (
    <ul className="ana-types">
      {types.map(([type, count]) => (
        <li key={type} className="ana-type-row">
          <span className="ana-type-row__label">{type.replace(/_/g, " ")}</span>
          <svg
            viewBox="0 0 100 8"
            preserveAspectRatio="none"
            role="img"
            aria-label={`${type}: ${count}`}
          >
            <rect x={0} y={0} width={100} height={8} className="ana-fill--track" />
            <rect x={0} y={0} width={(count / max) * 100} height={8} className="ana-fill--type" />
          </svg>
          <span className="ana-type-row__count">{count}</span>
        </li>
      ))}
    </ul>
  );
}

function ActivityChart({ starts, counts }: { starts: Date[]; counts: number[] }) {
  const W = 320;
  const H = 104;
  const PAD = 6;
  const BASE = 96;
  const TOP = 10;
  const max = Math.max(1, ...counts);
  const step = counts.length > 1 ? (W - PAD * 2) / (counts.length - 1) : 0;
  const points = counts.map((count, i) => ({
    x: PAD + i * step,
    y: BASE - (count / max) * (BASE - TOP),
  }));
  const line = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${(W - PAD).toFixed(1)} ${BASE} L${PAD} ${BASE} Z`;
  const label = `Assertions created per week, oldest to newest: ${counts.join(", ")}`;

  return (
    <div className="ana-chart-body ana-activity">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        <path d={area} className="ana-activity__area" />
        <path d={line} className="ana-activity__line" />
        {points.map((p, i) => (
          <circle
            key={starts[i].getTime()}
            cx={p.x}
            cy={p.y}
            r={2.5}
            className="ana-activity__dot"
          />
        ))}
      </svg>
      <div className="ana-activity__labels" aria-hidden="true">
        {starts.map((d) => (
          <span key={d.getTime()}>
            {d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          </span>
        ))}
      </div>
      <p className="ana-chart-note">
        Assertions created per ISO week · last {counts.length} weeks · peak{" "}
        {Math.max(0, ...counts)}/wk
      </p>
    </div>
  );
}

// --- Page -------------------------------------------------------------------

export function AnalyticsPage() {
  const session = useActiveSession();
  const matterId = session.currentMatter.id;

  const [items, setItems] = useState<Assertion[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [members, setMembers] = useState<Record<string, UserInfo>>({});
  const [summaries, setSummaries] = useState<Record<string, RatingSummary | null>>({});
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setLoadError(null);
    setMembers({});
    setSummaries({});

    api.listMatterMembers(matterId).then(
      (res) => {
        if (cancelled) return;
        setMembers(Object.fromEntries(res.items.map((m) => [m.user.id, m.user])));
      },
      () => {
        /* Names are a nicety — fall back to raw user ids. */
      },
    );

    api.listAssertions(matterId, {}).then(
      (list) => {
        if (cancelled) return;
        setItems(list.items);
        const rated = list.items
          .filter((a) => a.current_revision_number !== null)
          .slice(0, RATING_SUMMARY_CAP);
        for (const assertion of rated) {
          const revision = assertion.current_revision_number;
          if (revision === null) continue;
          api.ratingSummary(assertion.id, revision).then(
            (summary) => {
              if (!cancelled) {
                setSummaries((prev) => ({ ...prev, [assertion.id]: summary }));
              }
            },
            () => {
              if (!cancelled) {
                setSummaries((prev) => ({ ...prev, [assertion.id]: null }));
              }
            },
          );
        }
      },
      (error: unknown) => {
        if (cancelled) return;
        setLoadError(
          error instanceof Error ? error.message : "Failed to load assertions.",
        );
      },
    );

    return () => {
      cancelled = true;
    };
  }, [matterId, reloadKey]);

  const stats = useMemo(() => {
    if (items === null) return null;

    const statusCounts: Record<StatusBucketKey, number> = {
      accepted: 0,
      proposed: 0,
      disputed: 0,
      rejected: 0,
      other: 0,
    };
    let open = 0;
    let confidenceSum = 0;
    let confidenceCount = 0;
    const typeCounts = new Map<string, number>();
    const originGroups = {
      user_suggested: { accepted: 0, rejected: 0 },
      model_suggested: { accepted: 0, rejected: 0 },
    };
    const contributorMap = new Map<string, { authored: number; accepted: number }>();

    for (const a of items) {
      statusCounts[bucketOf(a.status)] += 1;
      if (
        a.status === "proposed" ||
        a.status === "revision_requested" ||
        a.status === "disputed"
      ) {
        open += 1;
      }
      typeCounts.set(a.assertion_type, (typeCounts.get(a.assertion_type) ?? 0) + 1);
      if (a.origin === "user_suggested" || a.origin === "model_suggested") {
        if (a.status === "accepted") originGroups[a.origin].accepted += 1;
        if (a.status === "rejected") originGroups[a.origin].rejected += 1;
      }
      if (a.origin === "model_suggested" && a.confidence !== null) {
        confidenceSum += a.confidence;
        confidenceCount += 1;
      }
      const contributor = contributorMap.get(a.author_user_id) ?? {
        authored: 0,
        accepted: 0,
      };
      contributor.authored += 1;
      if (a.status === "accepted") contributor.accepted += 1;
      contributorMap.set(a.author_user_id, contributor);
    }

    const reviewed = statusCounts.accepted + statusCounts.rejected;
    const topTypes = [...typeCounts.entries()]
      .sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
      .slice(0, TOP_TYPES);
    const topContributors: ContributorRow[] = [...contributorMap.entries()]
      .map(([userId, counts]) => ({ userId, ...counts }))
      .sort((x, y) => y.authored - x.authored || x.userId.localeCompare(y.userId))
      .slice(0, TOP_CONTRIBUTORS);

    return {
      total: items.length,
      accepted: statusCounts.accepted,
      open,
      reviewed,
      acceptanceRate: reviewed > 0 ? statusCounts.accepted / reviewed : null,
      avgConfidence: confidenceCount > 0 ? confidenceSum / confidenceCount : null,
      statusCounts,
      topTypes,
      originGroups,
      topContributors,
      activity: weeklyBuckets(items, ACTIVITY_WEEKS),
    };
  }, [items]);

  const ratedAverages = useMemo(
    () =>
      Object.values(summaries).filter(
        (s): s is RatingSummary => s !== null && s.count > 0 && s.average !== null,
      ),
    [summaries],
  );
  const avgStrength =
    ratedAverages.length > 0
      ? ratedAverages.reduce((sum, s) => sum + (s.average ?? 0), 0) /
        ratedAverages.length
      : null;

  const header = (
    <header className="page-header">
      <div>
        <h1 className="page-header__title">Analytics</h1>
        <p className="page-header__subtitle">
          {`Computed live from this matter's assertions · ${session.currentMatter.name}`}
        </p>
      </div>
    </header>
  );

  if (loadError) {
    return (
      <div className="ana-page">
        {header}
        <div className="error-banner">
          {loadError}{" "}
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => setReloadKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (items === null || stats === null) {
    return (
      <div className="ana-page">
        {header}
        <div className="loading">Loading analytics…</div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="ana-page">
        {header}
        <div className="empty-state">
          <p className="empty-state__title">No assertions yet</p>
          <p>Metrics appear once this matter has assertions to measure.</p>
        </div>
      </div>
    );
  }

  const originData: OriginDatum[] = [
    { key: "user_suggested", label: "Colleague-suggested", ...stats.originGroups.user_suggested },
    { key: "model_suggested", label: "AI-deduced", ...stats.originGroups.model_suggested },
  ];

  return (
    <div className="ana-page">
      {header}

      <div className="ana-kpis">
        <KpiCard id="total" label="Total assertions" value={stats.total} caption="all statuses" />
        <KpiCard id="accepted" label="Accepted" value={stats.accepted} caption="review status" />
        <KpiCard
          id="open"
          label="Open"
          value={stats.open}
          caption="proposed · revision requested · disputed"
        />
        <KpiCard
          id="acceptance"
          label="Acceptance rate"
          value={
            stats.acceptanceRate === null
              ? "—"
              : `${Math.round(stats.acceptanceRate * 100)}%`
          }
          caption={
            stats.reviewed > 0
              ? `of ${stats.reviewed} reviewed`
              : "no reviewed assertions yet"
          }
        />
        <KpiCard
          id="strength"
          label="Avg strength rating"
          value={avgStrength === null ? "—" : `${avgStrength.toFixed(1)} / 5`}
          caption={
            ratedAverages.length > 0
              ? `1–5 scale · ${ratedAverages.length} rated`
              : "no ratings yet"
          }
        />
        <KpiCard
          id="confidence"
          label="Avg model confidence"
          value={
            stats.avgConfidence === null
              ? "—"
              : `${Math.round(stats.avgConfidence * 100)}%`
          }
          caption="AI-deduced assertions only"
        />
      </div>

      <div className="ana-charts">
        <section className="card">
          <div className="card__header">Status mix</div>
          <div className="card__body">
            <StatusMixChart counts={stats.statusCounts} />
          </div>
        </section>

        <section className="card">
          <div className="card__header">Acceptance by origin</div>
          <div className="card__body">
            <OriginChart data={originData} />
          </div>
        </section>

        <section className="card">
          <div className="card__header">
            Assertions by type
            <span className="ana-card-note">top {TOP_TYPES}</span>
          </div>
          <div className="card__body">
            <TypeBars types={stats.topTypes} />
          </div>
        </section>

        <section className="card">
          <div className="card__header">Review activity</div>
          <div className="card__body">
            <ActivityChart starts={stats.activity.starts} counts={stats.activity.counts} />
          </div>
        </section>
      </div>

      <div className="card">
        <div className="card__header">
          Top contributors
          <span className="ana-card-note">by authored assertions</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Contributor</th>
                <th className="ana-num">Authored</th>
                <th className="ana-num">Accepted</th>
              </tr>
            </thead>
            <tbody>
              {stats.topContributors.map((c) => {
                const user = members[c.userId];
                return (
                  <tr key={c.userId}>
                    <td>
                      <span className="ana-contrib">
                        <span className="avatar" aria-hidden="true">
                          {initialsOf(user?.display_name)}
                        </span>
                        {user ? (
                          <span className="ana-contrib__name">{user.display_name}</span>
                        ) : (
                          <span className="mono">{c.userId}</span>
                        )}
                      </span>
                    </td>
                    <td className="ana-num">{c.authored}</td>
                    <td className="ana-num">{c.accepted}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
