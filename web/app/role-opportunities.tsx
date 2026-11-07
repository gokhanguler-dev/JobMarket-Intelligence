"use client";

import { useState } from "react";

type Opportunity = {
  id: number;
  role: string;
  title: string;
  company: string;
  location: string | null;
  scope: "turkiye" | "remote_from_turkiye";
  source: string;
  url: string;
  checked_at: string;
  expires_at: string;
  days_seen: number;
  technologies: string[];
  capabilities: string[];
};

export type OpportunityReport = {
  window_days: number;
  window_end: string;
  minimum_days: number;
  jobs: Opportunity[];
};

const timestamp = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "Europe/Istanbul",
});

function Signals({ label, values }: { label: string; values: string[] }) {
  if (!values.length) return null;
  return (
    <div>
      <h4>{label}</h4>
      <ul className="opportunity-signals">
        {values.map((value) => <li key={value}>{value}</li>)}
      </ul>
    </div>
  );
}

export function RoleOpportunities({ report }: { report: OpportunityReport }) {
  const [role, setRole] = useState("");
  const [signal, setSignal] = useState("");
  const roles = [...new Set(report.jobs.map((job) => job.role))];
  const roleJobs = report.jobs.filter((job) => !role || job.role === role);
  const signals = [...new Set(roleJobs.flatMap((job) => [...job.technologies, ...job.capabilities]))].sort();
  const jobs = roleJobs.filter((job) =>
    !signal || job.technologies.includes(signal) || job.capabilities.includes(signal)
  );

  return (
    <section id="role-opportunities" className="section alt-section" aria-labelledby="role-opportunities-heading">
      <div className="shell">
        <div className="section-heading">
          <div>
            <span className="section-label">POSTINGS TO EXPLORE</span>
            <h2 id="role-opportunities-heading">Recently seen on employer boards</h2>
          </div>
          <p>
            Türkiye-eligible postings seen on at least {report.minimum_days} separate days in the
            { " " }{report.window_days}-day window through {report.window_end}. Each card shows the
            last successful board check.
          </p>
        </div>

        {report.jobs.length > 0 && (
          <div className="trend-controls role-sample-controls">
            <label>
              Role
              <select aria-label="Opportunity role" value={role} onChange={(event) => {
                setRole(event.target.value);
                setSignal("");
              }}>
                <option value="">All roles</option>
                {roles.map((name) => <option key={name}>{name}</option>)}
              </select>
            </label>
            <label>
              Technology or capability
              <select aria-label="Opportunity signal" value={signal} onChange={(event) => setSignal(event.target.value)}>
                <option value="">All signals</option>
                {signals.map((name) => <option key={name}>{name}</option>)}
              </select>
            </label>
          </div>
        )}

        {jobs.length === 0 && (
          <p>{report.jobs.length > 0
            ? "No postings match these filters."
            : "No recent board checks meet the evidence threshold yet."}</p>
        )}

        <div className="role-evidence-grid">
          {jobs.map((job) => (
            <article className="panel evidence-panel opportunity-card" key={job.id}>
              <div>
                <p className="opportunity-employer">{job.company} · {job.role}</p>
                <h3>{job.title}</h3>
                <p>
                  {job.scope === "remote_from_turkiye" ? "Remote from Türkiye" : job.location || "Türkiye"}
                  {" · "}{job.source}
                </p>
              </div>
              <p className="opportunity-observed">
                <strong>{job.days_seen} distinct days</strong> in the {report.window_days}-day window
                <br />
                Board checked <time dateTime={job.checked_at}>{timestamp.format(new Date(job.checked_at))}</time> (Türkiye time)
              </p>
              <Signals label="Detected capabilities" values={job.capabilities} />
              <Signals label="Mentioned technologies" values={job.technologies} />
              <a className="opportunity-link" href={job.url} target="_blank" rel="noreferrer">View employer posting ↗</a>
            </article>
          ))}
        </div>

        <p className="trend-notes">
          The day count measures when the posting appeared in collected snapshots.
          Check the employer page for application status and deadlines.
        </p>
      </div>
    </section>
  );
}
