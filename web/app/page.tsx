const skills = [
  { name: "Python", jobs: 29, width: 100 },
  { name: "Azure", jobs: 21, width: 72 },
  { name: "Databricks", jobs: 17, width: 59 },
  { name: "SQL", jobs: 17, width: 59 },
  { name: "AWS", jobs: 14, width: 48 },
  { name: "Spark", jobs: 13, width: 45 },
  { name: "Power BI", jobs: 10, width: 34 },
];

const pipeline = [
  {
    number: "01",
    title: "Sources",
    description: "Jooble, Lever & first-party career APIs",
  },
  {
    number: "02",
    title: "Python",
    description: "Collection, parsing & normalization",
  },
  {
    number: "03",
    title: "SQL Server",
    description: "RAW, staging & dimensional warehouse",
  },
  {
    number: "04",
    title: "dbt",
    description: "Tests, transformations & analytical marts",
  },
  {
    number: "05",
    title: "Airflow",
    description: "Scheduled orchestration & monitoring",
  },
  {
    number: "06",
    title: "Analytics",
    description: "Interactive market intelligence",
  },
];

export default function Home() {
  return (
    <main>
      <div className="site-shell">
        <nav className="navbar">
          <a className="logo" href="#">
            <span className="logo-mark">JM</span>
            <span>JobMarket Intelligence</span>
          </a>

          <div className="nav-links">
            <a href="#market">Market</a>
            <a href="#recommendations">Learn Next</a>
            <a href="#architecture">Architecture</a>
            <a
              className="github-button"
              href="https://github.com/gokhanguler-dev/JobMarket-Intelligence"
              target="_blank"
              rel="noreferrer"
            >
              GitHub ↗
            </a>
          </div>
        </nav>

        <section className="hero">
          <div className="hero-badge">
            TURKEY • DATA & ANALYTICS JOB MARKET
          </div>

          <h1>
            The data job market,
            <br />
            <span className="hero-gradient">decoded through data.</span>
          </h1>

          <p className="hero-copy">
            JobMarket Intelligence transforms job postings into actionable
            insights about technology demand, role expectations and the skills
            data professionals should learn next.
          </p>

          <div className="hero-actions">
            <a className="primary-button" href="#market">
              Explore the market ↓
            </a>

            <a className="secondary-button" href="#architecture">
              View architecture
            </a>
          </div>

          <div className="metric-grid">
            <div className="metric">
              <div className="metric-value">346</div>
              <div className="metric-label">Unique job postings</div>
            </div>

            <div className="metric">
              <div className="metric-value">75</div>
              <div className="metric-label">Companies observed</div>
            </div>

            <div className="metric">
              <div className="metric-value">32</div>
              <div className="metric-label">Technology skills tracked</div>
            </div>

            <div className="metric">
              <div className="metric-value">3</div>
              <div className="metric-label">Integrated data sources</div>
            </div>
          </div>
        </section>
      </div>

      <section id="market" className="section section-border">
        <div className="site-shell">
          <span className="eyebrow">Market Intelligence</span>

          <h2 className="section-title">
            What technologies are companies hiring for?
          </h2>

          <p className="section-description">
            Technology demand is extracted directly from observed job postings
            and modeled across companies, roles and data sources.
          </p>

          <div className="skills-layout">
            <div className="skill-list">
              {skills.map((skill) => (
                <div className="skill-row" key={skill.name}>
                  <span className="skill-name">{skill.name}</span>

                  <div className="skill-track">
                    <div
                      className="skill-bar"
                      style={{ width: `${skill.width}%` }}
                    />
                  </div>

                  <span className="skill-count">{skill.jobs}</span>
                </div>
              ))}
            </div>

            <div className="recommendation-card">
              <span className="eyebrow">Market Signal</span>

              <h3
                style={{
                  fontSize: "27px",
                  margin: "15px 0 12px",
                  letterSpacing: "-0.035em",
                }}
              >
                Python leads current technology demand.
              </h3>

              <p
                style={{
                  color: "var(--muted)",
                  lineHeight: 1.7,
                  margin: 0,
                }}
              >
                Cloud and modern data-platform technologies also rank
                prominently, with Azure, Databricks, AWS and Spark appearing
                across observed data roles.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section
        id="recommendations"
        className="section section-border"
      >
        <div className="site-shell">
          <span className="eyebrow">Career Intelligence</span>

          <h2 className="section-title">
            What should I learn next?
          </h2>

          <p className="section-description">
            Match the technologies you already know against real market demand
            for your target role.
          </p>

          <div className="skills-layout">
            <div>
              <p className="recommendation-label">TARGET ROLE</p>
              <div className="role-pill">Data Engineer</div>

              <p
                className="recommendation-label"
                style={{ marginTop: "28px" }}
              >
                SKILLS YOU ALREADY KNOW
              </p>

              <div className="known-skills">
                <span className="known-skill">✓ SQL</span>
                <span className="known-skill">✓ Python</span>
                <span className="known-skill">✓ Docker</span>
                <span className="known-skill">✓ SSIS</span>
              </div>

              <p className="section-description">
                Recommendations are ranked from technologies appearing most
                frequently in postings for the selected role.
              </p>
            </div>

            <div className="recommendation-card">
              <p className="recommendation-label">
                RECOMMENDED NEXT SKILLS
              </p>

              <div className="recommendations">
                <div className="recommendation">
                  <strong>Azure</strong>
                  <span>HIGH DEMAND</span>
                </div>

                <div className="recommendation">
                  <strong>Databricks</strong>
                  <span>HIGH DEMAND</span>
                </div>

                <div className="recommendation">
                  <strong>Spark</strong>
                  <span>MARKET SIGNAL</span>
                </div>

                <div className="recommendation">
                  <strong>Airflow</strong>
                  <span>MARKET SIGNAL</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="architecture"
        className="section section-border"
      >
        <div className="site-shell">
          <span className="eyebrow">Under the Hood</span>

          <h2 className="section-title">
            Built as a data engineering platform.
          </h2>

          <p className="section-description">
            The dashboard is the final layer of a multi-source pipeline that
            collects, standardizes, models, tests and orchestrates job-market
            data.
          </p>

          <div className="pipeline">
            {pipeline.map((step) => (
              <div className="pipeline-step" key={step.number}>
                <div className="pipeline-number">{step.number}</div>

                <div className="pipeline-title">{step.title}</div>

                <div className="pipeline-description">
                  {step.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="site-shell footer-content">
          <span>JobMarket Intelligence</span>

          <span>
            Python • SQL Server • dbt • Airflow • Next.js
          </span>
        </div>
      </footer>
    </main>
  );
}