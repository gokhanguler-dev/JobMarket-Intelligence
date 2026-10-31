export const dynamic = "force-dynamic";

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
  capability_count: number;
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

type CapabilityDemand = {
  CareerAreaName: string;
  RoleName: string;
  Seniority: string;
  CapabilityCategory: string;
  CapabilityName: string;
  CapabilityJobCount: number;
  CompanyCount: number;
  SourceCount: number;
  RoleSeniorityJobCount: number;
  CapabilityDemandPercentage: number;
};

async function getMarketData() {
  const fs = await import("fs/promises");
  const path = await import("path");

  const dataDirectory = path.join(process.cwd(), "public", "data");

  const [
    metadataRaw,
    skillDemandRaw,
    capabilityDemandRaw,
  ] = await Promise.all([
    fs.readFile(
      path.join(dataDirectory, "metadata.json"),
      "utf-8"
    ),

    fs.readFile(
      path.join(dataDirectory, "skill-demand.json"),
      "utf-8"
    ),

    fs.readFile(
      path.join(dataDirectory, "role-capability-demand.json"),
      "utf-8"
    ),
  ]);

  return {
    metadata: JSON.parse(metadataRaw) as Metadata,
    skills: JSON.parse(skillDemandRaw) as SkillDemand[],
    capabilities: JSON.parse(
      capabilityDemandRaw
    ) as CapabilityDemand[],
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

function formatSources(sources: string[]) {
  return sources.join(" · ");
}

function getEvidenceLabel(
  capabilityJobCount: number,
  roleSeniorityJobCount: number,
) {
  if (
    roleSeniorityJobCount >= 8 &&
    capabilityJobCount >= 4
  ) {
    return "STRONGER EVIDENCE";
  }

  if (
    roleSeniorityJobCount >= 4 &&
    capabilityJobCount >= 2
  ) {
    return "MODERATE EVIDENCE";
  }

  return "LIMITED SAMPLE";
}

export default async function Home() {
  const {
    metadata,
    skills,
    capabilities,
  } = await getMarketData();

  // -------------------------------------------------------
  // TECHNOLOGY DEMAND
  // -------------------------------------------------------

  const topSkills = skills.slice(0, 10);

  const leadingSkill = topSkills[0];

  const maxJobCount =
    leadingSkill?.JobCount || 1;

  // -------------------------------------------------------
  // CAPABILITY DEMAND
  //
  // Avoid allowing tiny 1-of-1 segments to dominate the
  // public showcase purely because they equal 100%.
  // The underlying JSON still contains the full mart.
  // -------------------------------------------------------

  const showcaseCapabilities = capabilities
    .filter(
      (capability) =>
        capability.RoleSeniorityJobCount >= 3 &&
        capability.CapabilityJobCount >= 2,
    )
    .sort((a, b) => {
      if (
        b.CapabilityDemandPercentage !==
        a.CapabilityDemandPercentage
      ) {
        return (
          b.CapabilityDemandPercentage -
          a.CapabilityDemandPercentage
        );
      }

      if (
        b.CapabilityJobCount !==
        a.CapabilityJobCount
      ) {
        return (
          b.CapabilityJobCount -
          a.CapabilityJobCount
        );
      }

      return (
        b.RoleSeniorityJobCount -
        a.RoleSeniorityJobCount
      );
    })
    .slice(0, 8);

  const leadingCapability =
    showcaseCapabilities[0];

  return (
    <main>
      {/* ===================================================
          NAVIGATION
      =================================================== */}

      <nav className="navbar">
        <div className="shell nav-inner">
          <a className="brand" href="#">
            Career <span>Radar</span>
          </a>

          <div className="nav-links">
            <a href="#market">
              Technologies
            </a>

            <a href="#capabilities">
              Capabilities
            </a>

            <a href="#career">
              Career Radar
            </a>

            <a href="#architecture">
              Architecture
            </a>

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

      {/* ===================================================
          HERO
      =================================================== */}

      <section className="hero">
        <div className="hero-glow hero-glow-one" />
        <div className="hero-glow hero-glow-two" />

        <div className="shell hero-grid">
          <div className="hero-content">
            <div className="eyebrow">
              TURKEY · TECH CAREER INTELLIGENCE
            </div>

            <h1>
              Understand the market.
              <span>
                {" "}
                Understand your next move.
              </span>
            </h1>

            <p className="hero-copy">
              Technology job postings transformed into
              structured intelligence across careers,
              roles, seniority, technologies and
              professional capabilities.
            </p>

            <div className="hero-actions">
              <a
                className="primary-button"
                href="#market"
              >
                Explore the Market
              </a>

              <a
                className="secondary-button"
                href="#career"
              >
                Discover Career Radar ↓
              </a>
            </div>
          </div>

          {/* -----------------------------------------------
              DATA FRESHNESS
          ----------------------------------------------- */}

          <div className="freshness-card">
            <div className="freshness-header">
              <div>
                <span className="panel-kicker">
                  PIPELINE STATUS
                </span>

                <h3>Market data freshness</h3>
              </div>

              <span className="status-badge">
                <i />
                {metadata.pipeline_status}
              </span>
            </div>

            <div className="freshness-main">
              <span>LAST DATA UPDATE</span>

              <strong>
                {formatDate(metadata.last_updated)}
              </strong>

              <small>Europe/Istanbul</small>
            </div>

            <div className="schedule-grid">
              <div className="schedule-item">
                <span>NEXT DAILY RUN</span>

                <strong>
                  {formatDate(
                    metadata.daily_pipeline.next_run,
                  )}
                </strong>

                <small>
                  {formatSources(
                    metadata.daily_pipeline.sources,
                  )}
                </small>
              </div>

              <div className="schedule-item">
                <span>NEXT JOOBLE RUN</span>

                <strong>
                  {formatDate(
                    metadata.jooble_pipeline.next_run,
                  )}
                </strong>

                <small>
                  Quota-aware market refresh
                </small>
              </div>
            </div>

            <div className="snapshot-time">
              Snapshot generated{" "}
              {formatDate(
                metadata.snapshot_generated_at,
              )}
            </div>
          </div>
        </div>

        {/* -----------------------------------------------
            LIVE MARKET KPIs
        ----------------------------------------------- */}

        <div className="shell">
          <div className="metrics metrics-five">
            <div className="metric">
              <strong>
                {metadata.job_count}
              </strong>

              <span>Job Postings</span>
            </div>

            <div className="metric">
              <strong>
                {metadata.company_count}
              </strong>

              <span>Companies</span>
            </div>

            <div className="metric">
              <strong>
                {metadata.skill_count}
              </strong>

              <span>Technologies</span>
            </div>

            <div className="metric">
              <strong>
                {metadata.capability_count}
              </strong>

              <span>Capabilities</span>
            </div>

            <div className="metric">
              <strong>
                {metadata.source_count}
              </strong>

              <span>Data Sources</span>
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================
          TECHNOLOGY DEMAND
      =================================================== */}

      <section
        id="market"
        className="section"
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">
                MARKET INTELLIGENCE
              </span>

              <h2>
                What technologies are companies
                <br />
                looking for?
              </h2>
            </div>

            <p>
              Technology demand calculated from
              unique job postings across the current
              multi-source technology job market.
            </p>
          </div>

          <div className="market-grid">
            <div className="panel skill-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-kicker">
                    TECHNOLOGY DEMAND
                  </span>

                  <h3>
                    Most requested technologies
                  </h3>
                </div>

                <span className="live-badge">
                  <i />
                  LIVE DATA
                </span>
              </div>

              <div className="skill-list">
                {topSkills.map(
                  (skill, index) => {
                    const width =
                      (skill.JobCount /
                        maxJobCount) *
                      100;

                    return (
                      <div
                        className="skill-row"
                        key={skill.SkillKey}
                      >
                        <div className="skill-meta">
                          <div className="skill-name">
                            <span>
                              {String(
                                index + 1,
                              ).padStart(2, "0")}
                            </span>

                            <strong>
                              {skill.SkillName}
                            </strong>
                          </div>

                          <div className="skill-value">
                            <strong>
                              {skill.JobCount}
                            </strong>

                            <span>
                              jobs ·{" "}
                              {skill.DemandPercentage.toFixed(
                                2,
                              )}
                              %
                            </span>
                          </div>
                        </div>

                        <div className="skill-track">
                          <div
                            className="skill-fill"
                            style={{
                              width: `${width}%`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  },
                )}
              </div>
            </div>

            <aside className="signal-card">
              <span className="panel-kicker">
                MARKET SIGNAL
              </span>

              <div className="signal-icon">
                ↗
              </div>

              <div className="signal-number">
                {leadingSkill
                  ? `${leadingSkill.DemandPercentage.toFixed(
                      2,
                    )}%`
                  : "—"}
              </div>

              <h3>
                {leadingSkill
                  ? `${leadingSkill.SkillName} leads current technology demand.`
                  : "Technology demand is being calculated."}
              </h3>

              {leadingSkill && (
                <p>
                  Found in{" "}
                  <strong>
                    {leadingSkill.JobCount} job
                    postings
                  </strong>{" "}
                  across{" "}
                  <strong>
                    {leadingSkill.CompanyCount}{" "}
                    companies
                  </strong>{" "}
                  and{" "}
                  <strong>
                    {leadingSkill.SourceCount}{" "}
                    sources
                  </strong>
                  .
                </p>
              )}

              <div className="signal-divider" />

              <div className="signal-footer">
                <span>MARKET BASE</span>

                <strong>
                  {metadata.job_count} unique jobs
                </strong>
              </div>
            </aside>
          </div>
        </div>
      </section>

      {/* ===================================================
          CAPABILITY INTELLIGENCE
      =================================================== */}

      <section
        id="capabilities"
        className="section alt-section"
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">
                CAPABILITY INTELLIGENCE
              </span>

              <h2>
                Beyond tools.
                <br />
                What can the market expect you to do?
              </h2>
            </div>

            <p>
              Technologies show which tools employers
              request. Capabilities reveal the work
              professionals are expected to perform
              with those tools.
            </p>
          </div>

          <div className="capability-layout">
            <div className="panel capability-panel">
              <div className="panel-header">
                <div>
                  <span className="panel-kicker">
                    ROLE × SENIORITY DEMAND
                  </span>

                  <h3>
                    Strong capability signals
                  </h3>
                </div>

                <span className="live-badge">
                  <i />
                  LIVE DATA
                </span>
              </div>

              <div className="capability-list">
                {showcaseCapabilities.map(
                  (capability, index) => (
                    <div
                      className="capability-row"
                      key={[
                        capability.CareerAreaName,
                        capability.RoleName,
                        capability.Seniority,
                        capability.CapabilityName,
                      ].join("-")}
                    >
                      <div className="capability-top">
                        <div className="capability-title">
                          <span>
                            {String(
                              index + 1,
                            ).padStart(2, "0")}
                          </span>

                          <div>
                            <strong>
                              {
                                capability.CapabilityName
                              }
                            </strong>

                            <small>
                              {
                                capability.RoleName
                              }{" "}
                              ·{" "}
                              {
                                capability.Seniority
                              }
                            </small>
                          </div>
                        </div>

                        <div className="capability-score">
                          <strong>
                            {capability.CapabilityDemandPercentage.toFixed(
                              2,
                            )}
                            %
                          </strong>

                          <span>
                            {
                              capability.CapabilityJobCount
                            }{" "}
                            of{" "}
                            {
                              capability.RoleSeniorityJobCount
                            }{" "}
                            jobs
                          </span>
                        </div>
                      </div>

                      <div className="skill-track capability-track">
                        <div
                          className="skill-fill"
                          style={{
                            width: `${Math.min(
                              capability.CapabilityDemandPercentage,
                              100,
                            )}%`,
                          }}
                        />
                      </div>

                      <div className="capability-evidence">
                        <span>
                          {
                            capability.CapabilityCategory
                          }
                        </span>

                        <span>
                          {
                            capability.CompanyCount
                          }{" "}
                          companies ·{" "}
                          {
                            capability.SourceCount
                          }{" "}
                          sources
                        </span>

                        <strong>
                          {getEvidenceLabel(
                            capability.CapabilityJobCount,
                            capability.RoleSeniorityJobCount,
                          )}
                        </strong>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </div>

            <aside className="signal-card capability-signal">
              <span className="panel-kicker">
                WHY CAPABILITIES?
              </span>

              <div className="signal-icon">
                ◇
              </div>

              <div className="signal-number">
                {metadata.capability_count}
              </div>

              <h3>
                Structured professional
                capabilities tracked across the
                market.
              </h3>

              <p>
                Instead of inferring capabilities
                from job titles alone, the model
                looks for explicit evidence in job
                descriptions and validates it
                against role and career context.
              </p>

              {leadingCapability && (
                <>
                  <div className="signal-divider" />

                  <div className="signal-footer">
                    <span>
                      CURRENT STRONG SIGNAL
                    </span>

                    <strong>
                      {
                        leadingCapability.CapabilityName
                      }
                    </strong>

                    <small>
                      {
                        leadingCapability.RoleName
                      }{" "}
                      ·{" "}
                      {
                        leadingCapability.Seniority
                      }{" "}
                      ·{" "}
                      {leadingCapability.CapabilityDemandPercentage.toFixed(
                        2,
                      )}
                      %
                    </small>
                  </div>
                </>
              )}
            </aside>
          </div>
        </div>
      </section>

      {/* ===================================================
          CAREER RADAR
      =================================================== */}

      <section
        id="career"
        className="section"
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">
                CAREER INTELLIGENCE
              </span>

              <h2>
                Don't just search for your next job.
                <br />
                Understand your next move.
              </h2>
            </div>

            <p>
              Career Radar will turn market evidence
              into a personalized view of career fit,
              skill gaps and the next capabilities
              worth developing.
            </p>
          </div>

          <div className="recommendation-card">
            <div className="recommendation-main">
              <span className="panel-kicker">
                CAREER RADAR · COMING NEXT
              </span>

              <h3>
                Your career profile,
                <br />
                measured against the market.
              </h3>

              <p>
                The next intelligence layer will
                combine target role, seniority,
                technologies, capabilities and
                professional skills to explain where
                a profile is strong, where gaps exist
                and what should be learned next.
              </p>

              <div className="skill-group">
                <span className="skill-group-title">
                  MARKET MODEL
                </span>

                <div className="skill-chips">
                  <span>Career Areas</span>
                  <span>Roles</span>
                  <span>Seniority</span>
                  <span>Technologies</span>
                  <span>Capabilities</span>
                  <span>
                    Professional Skills · Next
                  </span>
                </div>
              </div>

              <div className="career-preview-grid">
                <div className="career-preview-item">
                  <span>01</span>
                  <strong>Market Fit</strong>
                  <small>
                    How closely your profile matches
                    your target market.
                  </small>
                </div>

                <div className="career-preview-item">
                  <span>02</span>
                  <strong>Critical Gaps</strong>
                  <small>
                    Missing skills and capabilities
                    backed by job-market evidence.
                  </small>
                </div>

                <div className="career-preview-item">
                  <span>03</span>
                  <strong>
                    What to Learn Next
                  </strong>
                  <small>
                    Prioritized recommendations
                    instead of generic technology
                    lists.
                  </small>
                </div>

                <div className="career-preview-item">
                  <span>04</span>
                  <strong>Market Changes</strong>
                  <small>
                    See how demand evolves after your
                    previous visit.
                  </small>
                </div>
              </div>
            </div>

            <div className="recommendation-side">
              <span className="recommendation-label">
                CAREER RADAR FLOW
              </span>

              <div className="next-skill">
                <span>01</span>
                <strong>
                  Choose a target role
                </strong>
              </div>

              <div className="next-skill">
                <span>02</span>
                <strong>
                  Set your seniority
                </strong>
              </div>

              <div className="next-skill">
                <span>03</span>
                <strong>
                  Add what you already know
                </strong>
              </div>

              <div className="next-skill">
                <span>04</span>
                <strong>
                  Measure your market fit
                </strong>
              </div>

              <div className="next-skill">
                <span>05</span>
                <strong>
                  Discover your next move
                </strong>
              </div>

              <small>
                Recommendations will be generated
                from observed market evidence rather
                than hardcoded career advice.
              </small>
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================
          ARCHITECTURE
      =================================================== */}

      <section
        id="architecture"
        className="section architecture-section alt-section"
      >
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="section-label">
                UNDER THE HOOD
              </span>

              <h2>
                From fragmented job postings
                <br />
                to career intelligence.
              </h2>
            </div>

            <p>
              A multi-source data platform separates
              collection, normalization,
              classification, modeling,
              orchestration and public serving.
            </p>
          </div>

          <div className="source-strip">
            <span>Jooble</span>
            <span>Lever</span>
            <span>Akbank</span>
            <span>Greenhouse</span>
            <span>Workday</span>
            <span>SmartRecruiters</span>
          </div>

          <div className="pipeline">
            <div className="pipeline-step">
              <span>01</span>

              <strong>Sources</strong>

              <small>
                Multi-source ATS and job-market
                ingestion
              </small>
            </div>

            <div className="pipeline-arrow">
              →
            </div>

            <div className="pipeline-step">
              <span>02</span>

              <strong>Python</strong>

              <small>
                Collection · parsing ·
                classification
              </small>
            </div>

            <div className="pipeline-arrow">
              →
            </div>

            <div className="pipeline-step">
              <span>03</span>

              <strong>SQL Server</strong>

              <small>
                Staging · dimensions · facts ·
                bridges
              </small>
            </div>

            <div className="pipeline-arrow">
              →
            </div>

            <div className="pipeline-step">
              <span>04</span>

              <strong>dbt</strong>

              <small>
                Testing · intermediate models ·
                analytics marts
              </small>
            </div>

            <div className="pipeline-arrow">
              →
            </div>

            <div className="pipeline-step">
              <span>05</span>

              <strong>Airflow</strong>

              <small>
                Daily scheduling · orchestration ·
                retries
              </small>
            </div>

            <div className="pipeline-arrow">
              →
            </div>

            <div className="pipeline-step">
              <span>06</span>

              <strong>Career Radar</strong>

              <small>
                Published market and career
                intelligence
              </small>
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================
          FOOTER
      =================================================== */}

      <footer>
        <div className="shell footer-inner">
          <div>
            <strong>
              Career Radar · Tech Career Intelligence
            </strong>

            <span>
              Modern Data Engineering Portfolio
              Project
            </span>
          </div>

          <div className="footer-stack">
            Python · SQL Server · dbt · Airflow ·
            Docker · Next.js
          </div>
        </div>
      </footer>
    </main>
  );
}