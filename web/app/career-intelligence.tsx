"use client";

import { useState } from "react";

type Signal = { name: string; jobs: number };
type Group = "technologies" | "capabilities";
type Cohort = "active" | "new";

export type Demand = {
  jobs: number;
  companies: number;
  sources: string[];
  technologies: Signal[];
  capabilities: Signal[];
};

export type CareerIntelligence = {
  profile_start: string;
  profile_end: string;
  roles: (Demand & { role: string })[];
  weeks: {
    start: string;
    first_day: string;
    last_day: string;
    observed_days: number;
    active: Demand;
    new: Demand;
  }[];
};

const dayFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

function dayLabel(day: string) {
  return dayFormatter.format(new Date(day + "T00:00:00Z"));
}

function SignalList({ label, signals }: { label: string; signals: Signal[] }) {
  return (
    <div>
      <h4>{label}</h4>
      {signals.length ? (
        <ul className="evidence-signals">
          {signals.map((signal) => (
            <li key={signal.name}>
              <span>{signal.name}</span>
              <strong>{signal.jobs}</strong>
            </li>
          ))}
        </ul>
      ) : (
        <p>No matching evidence in this period.</p>
      )}
    </div>
  );
}

export function RoleProfiles({ data }: { data: CareerIntelligence }) {
  return (
    <section id="role-profiles" className="section" aria-labelledby="role-profiles-heading">
      <div className="shell">
        <div className="section-heading">
          <div>
            <span className="section-label">ROLE PROFILES</span>
            <h2 id="role-profiles-heading">What employers ask for by role</h2>
          </div>
          <p>
            {dayLabel(data.profile_start)} to {dayLabel(data.profile_end)} · Latest
            observation per posting in the last 30 days. Each count shows how many
            postings contained that signal.
          </p>
        </div>
        <div className="role-evidence-grid">
          {data.roles.map((role) => (
            <article key={role.role} className="panel evidence-panel">
              <h3>{role.role}</h3>
              <p>
                {role.jobs} postings · {role.companies} employers · {role.sources.length} sources
              </p>
              {role.jobs > 0 ? (
                <div className="role-evidence-signals">
                  <SignalList label="Technologies" signals={role.technologies.slice(0, 8)} />
                  <SignalList label="Capabilities" signals={role.capabilities.slice(0, 8)} />
                </div>
              ) : (
                <p>No recent observations for this role.</p>
              )}
              {(role.technologies.length > 8 || role.capabilities.length > 8) && (
                <details>
                  <summary>All detected signals</summary>
                  <div className="role-evidence-signals">
                    <SignalList label="Technologies" signals={role.technologies} />
                    <SignalList label="Capabilities" signals={role.capabilities} />
                  </div>
                </details>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function MarketTrends({ weeks }: { weeks: CareerIntelligence["weeks"] }) {
  const [cohort, setCohort] = useState<Cohort>("active");
  const [group, setGroup] = useState<Group>("technologies");
  const [selected, setSelected] = useState("");
  const totals = new Map<string, number>();
  for (const week of weeks) {
    for (const demand of [week.active, week.new]) {
      for (const signal of demand[group]) {
        totals.set(signal.name, (totals.get(signal.name) ?? 0) + signal.jobs);
      }
    }
  }
  const ranked = [...totals].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const signalName = totals.has(selected) ? selected : ranked[0]?.[0] ?? "";
  const choices = [...totals.keys()].sort((a, b) => a.localeCompare(b));
  const points = weeks.map((week) => {
    const sample = week[cohort];
    const hits = sample[group].find((signal) => signal.name === signalName)?.jobs ?? 0;
    return { ...week, sample, hits, share: sample.jobs > 0 ? 100 * hits / sample.jobs : null };
  });
  const maxShare = Math.max(5, Math.ceil(Math.max(0, ...points.map((point) => point.share ?? 0)) / 5) * 5);
  const first = weeks[0];
  const last = weeks[weeks.length - 1];
  const periodTime = (value: string) => Date.parse(value + "T00:00:00Z");
  const firstTime = first ? periodTime(first.start) : 0;
  const span = last ? periodTime(last.start) - firstTime : 0;
  const x = (week: string) => span ? 45 + 630 * (periodTime(week) - firstTime) / span : 360;
  const y = (share: number) => 174 - 150 * share / maxShare;

  return (
    <section id="market-trends" className="section alt-section" aria-labelledby="market-trends-heading">
      <div className="shell">
        <div className="section-heading">
          <div>
            <span className="section-label">WEEKLY MARKET TRENDS</span>
            <h2 id="market-trends-heading">How demand changes over time</h2>
          </div>
          <p>
            Weekly share of observed technology postings that mention a technology
            or show evidence of a capability. The series updates when the data
            pipeline publishes a new snapshot.
          </p>
        </div>
        {first && last ? (
          <div className="panel evidence-panel">
            <div className="trend-controls">
              <label>
                Posting cohort
                <select aria-label="Posting cohort" value={cohort} onChange={(event) => setCohort(event.target.value as Cohort)}>
                  <option value="active">Observed that week</option>
                  <option value="new">First seen that week</option>
                </select>
              </label>
              <label>
                Signal type
                <select aria-label="Signal type" value={group} onChange={(event) => {
                  setGroup(event.target.value as Group);
                  setSelected("");
                }}>
                  <option value="technologies">Technology</option>
                  <option value="capabilities">Capability</option>
                </select>
              </label>
              <label>
                Signal
                <select aria-label="Signal" value={signalName} onChange={(event) => setSelected(event.target.value)}>
                  {choices.length === 0 && <option value="">No signals available</option>}
                  {choices.map((name) => <option key={name}>{name}</option>)}
                </select>
              </label>
            </div>

            {signalName && (
              <svg className="trend-chart" viewBox="0 0 700 205" role="img"
                aria-label={`Weekly demand share for ${signalName}`}>
                {[0, maxShare / 2, maxShare].map((tick) => (
                  <g key={tick}>
                    <line className="trend-gridline" x1="45" y1={y(tick)} x2="675" y2={y(tick)} />
                    <text x="39" y={y(tick) + 4} textAnchor="end">{tick}%</text>
                  </g>
                ))}
                {points.map((point, index) => {
                  const prior = points[index - 1];
                  if (point.share === null) return null;
                  const connects = prior?.share != null &&
                    periodTime(point.start) - periodTime(prior.start) === 7 * 86400000;
                  return (
                    <g key={point.start}>
                      {connects && prior.share !== null && (
                        <line className="trend-line" x1={x(prior.start)} y1={y(prior.share)}
                          x2={x(point.start)} y2={y(point.share)} />
                      )}
                      <circle className="trend-dot" cx={x(point.start)} cy={y(point.share)} r="5">
                        <title>{`${dayLabel(point.start)} · ${point.share.toFixed(1)}% (${point.hits}/${point.sample.jobs})`}</title>
                      </circle>
                    </g>
                  );
                })}
                <text x="45" y="197">{dayLabel(first.start)}</text>
                {last.start !== first.start && (
                  <text x="675" y="197" textAnchor="end">{dayLabel(last.start)}</text>
                )}
              </svg>
            )}

            <p className="trend-notes">
              Coverage starts {first.first_day} and runs through {last.last_day}.
              Observed uses the latest stored description each week. First seen
              uses the first stored description. Historical text is evaluated with
              today&apos;s classification and extraction rules. Changes in source
              coverage or partial weeks can shift the share.
            </p>

            <details>
              <summary>Weekly counts and source coverage</summary>
              <div className="technology-pairs-panel" tabIndex={0} role="region" aria-label="Weekly demand data">
                <table className="technology-pairs-table">
                  <thead><tr>
                    <th scope="col">Week of</th><th scope="col">Days observed</th>
                    <th scope="col">Sources</th><th scope="col">Postings</th>
                    <th scope="col">Matches</th><th scope="col">Share</th>
                  </tr></thead>
                  <tbody>
                    {[...points].reverse().map((point) => (
                      <tr key={point.start}>
                        <th scope="row">{point.start}</th>
                        <td>{point.observed_days}/7</td>
                        <td title={point.sample.sources.join(", ")}>{point.sample.sources.length}</td>
                        <td>{point.sample.jobs}</td>
                        <td>{point.hits}</td>
                        <td>{point.share === null ? "—" : `${point.share.toFixed(1)}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        ) : <p>No observation history is available yet.</p>}
      </div>
    </section>
  );
}
