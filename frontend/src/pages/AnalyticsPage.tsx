// AnalyticsPage — matter-scoped dashboard.
//
// Every number comes from ONE GET /matters/{id}/assertion-stats request, which
// aggregates the whole matter on the server, plus the member list (names).
// Downloading every assertion and 50 rating summaries instead took minutes
// at pipeline scale, and averaged ratings over the first 50 assertions only
// (audit finding ui:1). The three platform signals stay strictly separate:
// user strength ratings (1–5), model confidence (0–1, AI-deduced only, shown
// as %), and review status. Charts are hand-rolled inline SVG driven by
// design tokens — no chart lib.
//
// Assertions the definition-linking pipeline generated (origin
// system_generated) are stored accepted under the user who ran it, but nobody
// suggested or reviewed them (ui:4): they count in the status mix, and are
// left out of the acceptance rate and of the contributors table. Their
// per-author counts come from a second stats request, made only when the
// matter has any.

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import "../styles/pages/analytics.css";

import { api } from "../api/client";
import type { AssertionStats, AssertionStatus, UserInfo } from "../api/types";
import { useActiveSession } from "../app/session";

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

/** Local midnight on the Monday of the given date's ISO week. */
function startOfIsoWeek(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return d;
}

/** Bucket edges for the last `weeks` ISO weeks in the viewer's timezone: the
 * local Monday midnight that starts each week, oldest first, then the next
 * Monday. The server counts assertions created in each [edge, next edge). */
function weekEdges(weeks: number, now = new Date()): Date[] {
  const current = startOfIsoWeek(now);
  const edges: Date[] = [];
  for (let i = weeks - 1; i >= -1; i--) {
    const d = new Date(current);
    d.setDate(d.getDate() - i * 7);
    edges.push(d);
  }
  return edges;
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

/** Everything the dashboard shows, from the server's aggregates; `pipeline`
 * holds the system_generated assertions' own aggregates (null: none). */
function deriveStats(stats: AssertionStats, weekStarts: Date[], pipeline: AssertionStats | null) {
  const count = (status: AssertionStatus) => stats.by_status[status] ?? 0;
  const statusCounts: Record<StatusBucketKey, number> = {
    accepted: count("accepted"),
    proposed: count("proposed"),
    disputed: count("disputed"),
    rejected: count("rejected"),
    other: 0,
  };
  statusCounts.other = Math.max(
    0,
    stats.total -
      statusCounts.accepted -
      statusCounts.proposed -
      statusCounts.disputed -
      statusCounts.rejected,
  );
  const open = count("proposed") + count("revision_requested") + count("disputed");
  // Decisions people made: pipeline output is accepted without a review.
  const pipelineStatus = stats.by_origin_status.system_generated ?? {};
  const reviewedAccepted = Math.max(0, statusCounts.accepted - (pipelineStatus.accepted ?? 0));
  const reviewedRejected = Math.max(0, statusCounts.rejected - (pipelineStatus.rejected ?? 0));
  const reviewed = reviewedAccepted + reviewedRejected;
  const decisions = (origin: "user_suggested" | "model_suggested") => ({
    accepted: stats.by_origin_status[origin]?.accepted ?? 0,
    rejected: stats.by_origin_status[origin]?.rejected ?? 0,
  });
  const topTypes = Object.entries(stats.by_type)
    .sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
    .slice(0, TOP_TYPES);
  // Each author's own assertions, without the pipeline output run under
  // their name.
  const pipelineByAuthor = new Map((pipeline?.authors ?? []).map((a) => [a.user_id, a]));
  const topContributors: ContributorRow[] = stats.authors
    .map((author) => {
      const generated = pipelineByAuthor.get(author.user_id);
      return {
        userId: author.user_id,
        authored: author.total - (generated?.total ?? 0),
        accepted: (author.by_status.accepted ?? 0) - (generated?.by_status.accepted ?? 0),
      };
    })
    .filter((row) => row.authored > 0)
    .sort((x, y) => y.authored - x.authored || x.userId.localeCompare(y.userId))
    .slice(0, TOP_CONTRIBUTORS);

  return {
    total: stats.total,
    accepted: statusCounts.accepted,
    open,
    reviewed,
    acceptanceRate: reviewed > 0 ? reviewedAccepted / reviewed : null,
    pipelineCount: stats.by_origin.system_generated ?? 0,
    avgConfidence: stats.confidence_by_origin.model_suggested?.average ?? null,
    // Mean of the per-assertion averages over every rated current revision.
    avgStrength: stats.ratings.average_of_averages,
    ratedCount: stats.ratings.rated_assertions,
    statusCounts,
    topTypes,
    originGroups: {
      user_suggested: decisions("user_suggested"),
      model_suggested: decisions("model_suggested"),
    },
    topContributors,
    // Buckets come back in the order of the edges that were sent.
    activity: {
      starts: weekStarts,
      counts: weekStarts.map((_, i) => stats.created_buckets[i]?.count ?? 0),
    },
  };
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

  const [loaded, setLoaded] = useState<{
    stats: AssertionStats;
    weekStarts: Date[];
    pipeline: AssertionStats | null;
  } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // null until the roster has loaded (or when it could not be loaded).
  const [members, setMembers] = useState<Record<string, UserInfo> | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoaded(null);
    setLoadError(null);
    setMembers(null);

    api.listMatterMembers(matterId).then(
      (res) => {
        if (cancelled) return;
        setMembers(Object.fromEntries(res.map((m) => [m.user.id, m.user])));
      },
      () => {
        /* Names are a nicety: contributors get a neutral label, never an id. */
      },
    );

    const edges = weekEdges(ACTIVITY_WEEKS);
    api
      .assertionStats(matterId, {
        created_bucket_edges: edges.map((edge) => edge.toISOString()).join(","),
      })
      .then(async (result) => {
        const pipeline =
          !cancelled && (result.by_origin.system_generated ?? 0) > 0
            ? await api.assertionStats(matterId, { origin: "system_generated" })
            : null;
        return { result, pipeline };
      })
      .then(
        ({ result, pipeline }) => {
          if (!cancelled) setLoaded({ stats: result, weekStarts: edges.slice(0, -1), pipeline });
        },
        (error: unknown) => {
          if (cancelled) return;
          setLoadError(
            error instanceof Error ? error.message : "Failed to load analytics.",
          );
        },
      );

    return () => {
      cancelled = true;
    };
  }, [matterId, reloadKey]);

  const stats = useMemo(
    () => (loaded === null ? null : deriveStats(loaded.stats, loaded.weekStarts, loaded.pipeline)),
    [loaded],
  );

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

  if (stats === null) {
    return (
      <div className="ana-page">
        {header}
        <div className="loading">Loading analytics…</div>
      </div>
    );
  }

  if (stats.total === 0) {
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
        <KpiCard
          id="total"
          label="Total assertions"
          value={formatCount(stats.total)}
          caption="all statuses"
        />
        <KpiCard
          id="accepted"
          label="Accepted"
          value={formatCount(stats.accepted)}
          caption="review status"
        />
        <KpiCard
          id="open"
          label="Open"
          value={formatCount(stats.open)}
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
              ? `of ${formatCount(stats.reviewed)} reviewed`
              : "no reviewed assertions yet"
          }
        />
        <KpiCard
          id="strength"
          label="Avg strength rating"
          value={stats.avgStrength === null ? "—" : `${stats.avgStrength.toFixed(1)} / 5`}
          caption={
            stats.avgStrength !== null && stats.ratedCount > 0
              ? `1–5 scale · ${formatCount(stats.ratedCount)} rated`
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
                const user =
                  members?.[c.userId] ?? (c.userId === session.user.id ? session.user : undefined);
                // A user id is never a person's label (ui:0).
                const name = user
                  ? user.display_name
                  : members === null
                    ? "Team member"
                    : "Former member";
                return (
                  <tr key={c.userId}>
                    <td>
                      <span className="ana-contrib">
                        <span className="avatar" aria-hidden="true">
                          {initialsOf(user?.display_name)}
                        </span>
                        <span className={user ? "ana-contrib__name" : "ana-contrib__name muted"}>
                          {name}
                        </span>
                      </span>
                    </td>
                    <td className="ana-num">{formatCount(c.authored)}</td>
                    <td className="ana-num">{formatCount(c.accepted)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {stats.pipelineCount > 0 && (
          <p className="ana-chart-note ana-contrib-note">
            {`The ${formatCount(stats.pipelineCount)} assertions generated by the definition-linking pipeline are not credited to the person who ran it, and are left out of the acceptance rate.`}
          </p>
        )}
      </div>
    </div>
  );
}
