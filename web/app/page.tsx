type PipelineSchedule = {
  name: string;
  sources: string[];
  schedule: string;
  next_run: string;
};

type Metadata = {
  job_count: number;
  company_count: number;
  skill_count: number;
  source_count: number;
  last_updated: string | null;
  snapshot_generated_at: string;
  pipeline_status: string;
  daily_pipeline: PipelineSchedule;
  jooble_pipeline: PipelineSchedule;
};

type SkillDemand = {
  SkillKey: number;
  SkillName: string;
  JobCount: number;
  CompanyCount: number;
  SourceCount: number;
  TotalJobCount: number;
  DemandPercentage: number;
};

async function getMarketData() {
  const fs = await import("fs/promises");
  const path = await import("path");

  const dataDirectory = path.join(process.cwd(), "public", "data");

  const [metadataRaw, skillDemandRaw] = await Promise.all([
    fs.readFile(path.join(dataDirectory, "metadata.json"), "utf-8"),
    fs.readFile(path.join(dataDirectory, "skill-demand.json"), "utf-8"),
  ]);

  return {
    metadata: JSON.parse(metadataRaw) as Metadata,
    skills: JSON.parse(skillDemandRaw) as SkillDemand[],
  };
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Istanbul",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export default async function Home() {
  const { metadata, skills } = await getMarketData();

  const topSkills = skills.slice(0, 10);
  const leadingSkill = topSkills[0];
  const maxJobCount = leadingSkill?.JobCount || 1;

  return (
    <main>
      <nav className="navbar">
        <div className="shell nav-inner">
          <a className="brand" href="#">
            Tech Job Market <span>Intelligence</span>
          </a>

          <div className="nav-links">
            <a href="#market">Market</a>
            <a href="#career">Career Intelligence</a>
            <a href="#architecture">Architecture</a>

            <a
              className="github-link"
              href="https://github.com/gokhanguler-dev/JobMarket-Intelligence"
              target="_blank"
              rel="noreferrer"
            >
              GitHub ↗
            </a>
          </div>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-glow hero-glow-one" />
        <div className="hero-glow hero-glow-two" />

        <div className="shell hero-grid">
          <div className="hero-content">
            <div className="eyebrow">
              TURKEY · TECHNOLOGY JOB MARKET
            </div>

            <h1>
              The tech job market,
              <span> decoded through data.</span>
            </h1>

            <p className="hero-copy">
              Multi-source technology job postings transformed into role demand,
              technology signals and career intelligence through an end-to-end
              data engineering platform.
            </p>

            <div className="hero-actions">
              <a className="primary-button" href="#market">
                Explore the Market
              </a>

              <a
                className="secondary-button"
                href="https://github.com/gokhanguler-dev/JobMarket-Intelligence"
                target="_blank"
                rel="noreferrer"
              >
                View the Pipeline ↗
              </a>
            </div>
          </div>

          <div className="freshness-card">
            <div className="freshness-header">
              <div>
                <span className="panel-kicker">PIPELINE STATUS</span>
                <h3>Data freshness</h3>
              </div>

              <span className="status-badge">
                <i />
                {metadata.pipeline_status}
              </span>
            </div>

            <div className="freshness-main">
              <span>LAST DATA UPDATE</span>
              <strong>{formatDate(metadata.last_updated)}</strong>
              <small>Europe/Istanbul</small>
            </div>

            <div className="schedule-grid">
              <div className="schedule-item">
                <span>NEXT DAILY RUN</span>
                <strong>
                  {formatDate(metadata.daily_pipeline.next_run)}
                </strong>
                <small>Akbank + Lever</small>
              </div>

              <div className="schedule-item">
                <span>NEXT JOOBLE RUN</span>
                <strong>
                  {formatDate(metadata.jooble_pipeline.next_run)}
                </strong>
                <small>Quota-aware refresh</small>
              </div>
            </div>

            <div className="snapshot-time">
              Snapshot generated {formatDate(metadata.snapshot_generated_at)}
            </div>
          </div>
        </div>

        <div className="shell">
          <div className="metrics">
            <div className="metric">
              <strong>{metadata.job_count}</strong>
              <span>Job Postings</span>
            </div>

            <div className="metric">
              <strong>{metadata.company_count}</strong>
              <span>Companies</span>
            </div>

            <div className="metric">
              <strong>{metadata.skill_count}</strong>
              <span>Observed Technologies</span>
            </div>

            <div className="metric">
              <strong>{metadata.source_count}</strong>
              <span>Data Sources</span>
            </div>
          </div>
        </div>
      </section>

      <section id="market" className="section">
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">MARKET INTELLIGENCE</span>

              <h2>
                What technologies are companies
                <br />
                looking for?
              </h2>
            </div>

            <p>
              Technology demand calculated from unique job postings across
              the current multi-source job market dataset.
            </p>
          </div>

          <div className="market-grid">
            <div className="panel skill-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-kicker">TECHNOLOGY DEMAND</span>
                  <h3>Most requested technologies</h3>
                </div>

                <span className="live-badge">
                  <i />
                  LIVE DATA
                </span>
              </div>

              <div className="skill-list">
                {topSkills.map((skill, index) => {
                  const width =
                    (skill.JobCount / maxJobCount) * 100;

                  return (
                    <div className="skill-row" key={skill.SkillKey}>
                      <div className="skill-meta">
                        <div className="skill-name">
                          <span>
                            {String(index + 1).padStart(2, "0")}
                          </span>

                          <strong>{skill.SkillName}</strong>
                        </div>

                        <div className="skill-value">
                          <strong>{skill.JobCount}</strong>

                          <span>
                            jobs · {skill.DemandPercentage.toFixed(2)}%
                          </span>
                        </div>
                      </div>

                      <div className="skill-track">
                        <div
                          className="skill-fill"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <aside className="signal-card">
              <span className="panel-kicker">MARKET SIGNAL</span>

              <div className="signal-icon">↗</div>

              <div className="signal-number">
                {leadingSkill?.DemandPercentage.toFixed(2)}%
              </div>

              <h3>
                {leadingSkill?.SkillName} leads current technology demand.
              </h3>

              <p>
                Found in{" "}
                <strong>{leadingSkill?.JobCount} job postings</strong>{" "}
                across{" "}
                <strong>{leadingSkill?.CompanyCount} companies</strong>{" "}
                and{" "}
                <strong>{leadingSkill?.SourceCount} sources</strong>.
              </p>

              <div className="signal-divider" />

              <div className="signal-footer">
                <span>MARKET BASE</span>
                <strong>{metadata.job_count} unique jobs</strong>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section id="career" className="section alt-section">
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">CAREER INTELLIGENCE</span>
              <h2>From market demand to career decisions.</h2>
            </div>

            <p>
              Building a market-driven intelligence layer across roles,
              seniority, technologies and professional capabilities.
            </p>
          </div>

          <div className="recommendation-card">
            <div className="recommendation-main">
              <span className="panel-kicker">
                CAREER INTELLIGENCE · IN DEVELOPMENT
              </span>

              <h3>
                Understand the market.
                <br />
                Build the right career stack.
              </h3>

              <p>
                Job postings are being transformed into structured signals
                across career areas, normalized roles, seniority levels and
                technology demand. Capability and professional-skill
                intelligence will extend this model further.
              </p>

              <div className="skill-group">
                <span className="skill-group-title">
                  INTELLIGENCE LAYERS
                </span>

                <div className="skill-chips">
                  <span>Career Areas</span>
                  <span>Roles</span>
                  <span>Seniority</span>
                  <span>Technologies</span>
                  <span>Capabilities</span>
                  <span>Professional Skills</span>
                </div>
              </div>
            </div>

            <div className="recommendation-side">
              <span className="recommendation-label">
                CAREER RADAR · COMING NEXT
              </span>

              <div className="next-skill">
                <span>01</span>
                <strong>Choose a target role</strong>
              </div>

              <div className="next-skill">
                <span>02</span>
                <strong>Compare market demand</strong>
              </div>

              <div className="next-skill">
                <span>03</span>
                <strong>Identify technology gaps</strong>
              </div>

              <div className="next-skill">
                <span>04</span>
                <strong>Build a learning path</strong>
              </div>

              <small>
                Recommendations will be generated from observed market
                evidence rather than hardcoded technology lists.
              </small>
            </div>
          </div>
        </div>
      </section>

      <section id="architecture" className="section architecture-section">
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">UNDER THE HOOD</span>

              <h2>
                From fragmented postings
                <br />
                to market intelligence.
              </h2>
            </div>

            <p>
              A multi-layer data platform separates ingestion,
              transformation, classification, modeling, orchestration
              and serving.
            </p>
          </div>

          <div className="pipeline">
            <div className="pipeline-step">
              <span>01</span>
              <strong>Sources</strong>
              <small>Jooble · Lever · Akbank</small>
            </div>

            <div className="pipeline-arrow">→</div>

            <div className="pipeline-step">
              <span>02</span>
              <strong>Python</strong>
              <small>Collection · parsing · classification</small>
            </div>

            <div className="pipeline-arrow">→</div>

            <div className="pipeline-step">
              <span>03</span>
              <strong>SQL Server</strong>
              <small>Staging · dimensions · facts · bridges</small>
            </div>

            <div className="pipeline-arrow">→</div>

            <div className="pipeline-step">
              <span>04</span>
              <strong>dbt</strong>
              <small>Testing · analytics marts</small>
            </div>

            <div className="pipeline-arrow">→</div>

            <div className="pipeline-step">
              <span>05</span>
              <strong>Airflow</strong>
              <small>Scheduling · orchestration</small>
            </div>

            <div className="pipeline-arrow">→</div>

            <div className="pipeline-step">
              <span>06</span>
              <strong>Web</strong>
              <small>Published intelligence product</small>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className="shell footer-inner">
          <div>
            <strong>Tech Job Market Intelligence</strong>
            <span>Modern Data Engineering Portfolio Project</span>
          </div>

          <div className="footer-stack">
            Python · SQL Server · dbt · Airflow · Docker · Next.js
          </div>
        </div>
      </footer>
    </main>
  );
}