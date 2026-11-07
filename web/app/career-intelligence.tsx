"use client";

import { useState } from "react";
import type { OpportunityReport } from "./role-opportunities";

type Signal = { name: string; jobs: number; companies?: number };
type Group = "technologies" | "capabilities";
type Cohort = "active" | "new";

export type Demand = {
  jobs: number;
  companies: number;
  sources: string[];
  technologies: Signal[];
  capabilities: Signal[];
};

type MarketScope = "turkiye" | "remote_from_turkiye" | "aggregator_location_only" | "outside_turkiye" | "unknown";

type RoleAudit = {
  source_records: number;
  source_mix: Record<string, number>;
  distinct_postings: number;
  url_duplicates: number;
  excerpt_duplicates: number;
  possible_duplicate_records: number;
  locations: Record<MarketScope, number>;
};

type RoleProfile = Demand & {
  role: string;
  eligible?: Demand & { with_capability: number; with_strong_evidence: number };
  audit?: RoleAudit;
};

export type CareerIntelligence = {
  profile_start: string;
  profile_end: string;
  roles: RoleProfile[];
  opportunities?: OpportunityReport;
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
              <strong>
                {signal.jobs}
                {signal.companies !== undefined && (
                  <small>{signal.companies} {signal.companies === 1 ? "employer" : "employers"}</small>
                )}
              </strong>
            </li>
          ))}
        </ul>
      ) : (
        <p>No matching evidence in this period.</p>
      )}
    </div>
  );
}

function SampleAudit({ audit }: { audit: RoleAudit }) {
  const entries = [
    ["Source records", audit.source_records],
    ["Distinct postings after matching", audit.distinct_postings],
    ["Same posting URL", audit.url_duplicates],
    ["Matched syndication excerpts", audit.excerpt_duplicates],
    ["Possible duplicates still counted", audit.possible_duplicate_records],
    ["Türkiye location", audit.locations.turkiye],
    ["Remote from Türkiye", audit.locations.remote_from_turkiye],
    ["Aggregator country label only", audit.locations.aggregator_location_only],
    ["Outside Türkiye", audit.locations.outside_turkiye],
    ["Location unclear", audit.locations.unknown],
  ] as const;

  return (
    <details className="role-sample-audit">
      <summary>How this sample was checked</summary>
      <p>Source mix · {Object.entries(audit.source_mix).map(([source, count]) => `${source} ${count}`).join(" · ")}</p>
      <dl>
        {entries.map(([label, count]) => (
          <div key={label}><dt>{label}</dt><dd>{count}</dd></div>
        ))}
      </dl>
      <p>
        A syndication match requires the same title, compatible location and at
        least two matching excerpts in one direct posting. Possible duplicates
        stay in the sample. An aggregator country label alone stays outside the
        Türkiye sample until there is supporting location evidence.
      </p>
    </details>
  );
}

function RoleCard({ role, useEligible }: { role: RoleProfile; useEligible: boolean }) {
  const eligible = useEligible ? role.eligible : undefined;
  const sample = eligible ?? role;
  return (
    <article className="panel evidence-panel">
      <h3>{role.role}</h3>
      <p>{sample.jobs} postings · {sample.companies} employers · {sample.sources.length} sources</p>
      {eligible && (
        <p className="role-sample-coverage">
          {eligible.with_capability} with capability evidence · {eligible.with_strong_evidence} with a strong match
          {eligible.jobs > 0 && eligible.jobs < 10 && <small>Small sample</small>}
        </p>
      )}
      {sample.jobs > 0 ? (
        <div className="role-evidence-signals">
          <SignalList label="Technologies" signals={sample.technologies.slice(0, 8)} />
          <SignalList label="Capabilities" signals={sample.capabilities.slice(0, 8)} />
        </div>
      ) : (
        <p>No postings in this sample.</p>
      )}
      {(sample.technologies.length > 8 || sample.capabilities.length > 8) && (
        <details>
          <summary>All detected signals</summary>
          <div className="role-evidence-signals">
            <SignalList label="Technologies" signals={sample.technologies} />
            <SignalList label="Capabilities" signals={sample.capabilities} />
          </div>
        </details>
      )}
      {role.audit && <SampleAudit audit={role.audit} />}
    </article>
  );
}

export function RoleProfiles({ data }: { data: CareerIntelligence }) {
  const [sample, setSample] = useState("eligible");
  const audited = data.roles.some((role) => role.audit);
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
            observation per posting in the last 30 days. Signal counts show how
            many postings and identified employers provided evidence.
          </p>
        </div>
        {data.opportunities && (
          <p><a className="opportunity-link" href="#role-opportunities">Browse recently seen postings ↓</a></p>
        )}
        {audited && (
          <div className="trend-controls role-sample-controls">
            <label>
              Role sample
              <select aria-label="Role sample" value={sample} onChange={(event) => setSample(event.target.value)}>
                <option value="eligible">Türkiye location evidence</option>
                <option value="all">All source records</option>
              </select>
            </label>
          </div>
        )}
        <div className="role-evidence-grid">
          {data.roles.map((role) => (
            <RoleCard key={role.role} role={role} useEligible={sample === "eligible"} />
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
