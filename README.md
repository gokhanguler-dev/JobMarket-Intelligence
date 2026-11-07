# Career Radar — JobMarket Intelligence

> **Don't just search for your next job. Understand your next move.**

**Career Radar** is an end-to-end data engineering and career intelligence platform that continuously transforms multi-source technology job postings into structured market intelligence about roles, seniority, technologies, capabilities, companies, and employer demand.

The project preserves each collection as an observation so it can measure demand over time. [Live site](https://techcareerradar.com/) · [Role profiles](https://techcareerradar.com/#role-profiles) · [Weekly trends](https://techcareerradar.com/#market-trends)

The platform currently runs as a cloud-hosted pipeline that collects job postings, preserves historical observations, resolves canonical jobs, classifies technology roles, extracts technology and capability signals, builds analytical marts, and publishes curated data to a public-facing Next.js application.

The long-term goal is to turn this market intelligence into personalized career guidance:

**Where do I fit in the market, what am I missing, and what should I learn next?**

---

## Project Status

Career Radar has evolved from a local data engineering project into an operational multi-source cloud pipeline.

### Currently in Production

- Multi-source job ingestion
- Incremental market observations
- Canonical job identity resolution
- Technology / non-technology classification
- Career Area classification
- Normalized Role classification
- Seniority classification
- Technology extraction
- Capability extraction
- Technology co-occurrence with support, directional confidence, and lift
- Data Engineer and AI Engineer role profiles
- Weekly technology and capability trends from stored posting observations
- SQL Server dimensional warehouse
- dbt analytical marts and data-quality tests
- Apache Airflow orchestration
- JSON serving-layer publisher
- Next.js public web application
- Docker-based cloud deployment
- Caddy reverse proxy
- Scheduled autonomous ingestion

### Production Snapshot — November 7, 2026

| Metric | Value |
|---|---:|
| Canonical Job Postings | **762** |
| Postings Classified as Tech | **358** |
| Historical Job Observations | **18,711** |
| Companies | **87** |
| Technologies | **100** |
| Capability Definitions | **29** |
| Job ↔ Technology Relationships | **919** |
| Job ↔ Capability Relationships | **247** |
| Technology Pairs | **913** |
| Data Sources | **7** |

> The figures above describe the November 7 snapshot. Scheduled Airflow runs refresh the public data. [Current metadata](https://techcareerradar.com/data/metadata.json)

---

# Why This Project?

Traditional job boards are optimized around a question:

> **Which jobs can I apply to?**

Career Radar is designed around a different set of questions:

> **What does the technology job market currently demand?**

> **How does that demand differ by role and seniority?**

> **Where does my current profile fit into that market?**

> **What should I learn next?**

The platform is designed to answer questions such as:

- Which technology career areas are hiring?
- Which roles are most frequently observed?
- Which technologies are most requested?
- How does technology demand differ across roles?
- How does demand change by seniority?
- Which capabilities do employers expect beyond individual tools?
- Which technology stacks commonly appear together?
- Which companies request similar technology profiles?
- How is demand changing over time?
- Which skills provide the broadest market coverage?
- Which capabilities are important for a target role?
- What are the highest-value gaps in a professional's current profile?

The project therefore combines **data engineering**, **analytics engineering**, and an evolving **career intelligence product layer**.

---

# System Architecture

Career Radar separates ingestion, standardization, warehouse modeling, intelligence extraction, analytics, and serving into independent layers.

```text
                         EXTERNAL JOB SOURCES
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
       Job APIs                ATS APIs            Career Platforms
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                         Source Collectors
                                  │
                                  ▼
                        RAW Source Records
                                  │
                                  ▼
                      Standardized Staging
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              Canonical Jobs              Job Observations
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                         SQL Server DWH
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   Job Classification     Technology Extraction   Capability Extraction
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  ▼
                                 dbt
                                  │
                                  ▼
                         Analytical Marts
                                  │
                                  ▼
                         JSON Publisher
                                  │
                                  ▼
                       Next.js Career Radar
```

**Apache Airflow** orchestrates the complete workflow.

---

# Production Architecture

The production system runs continuously on a Linux cloud VPS using Docker Compose.

```text
                              INTERNET
                                 │
                                 ▼
                               Caddy
                         Reverse Proxy Layer
                                 │
                                 ▼
                         Next.js Career Radar
                                 │
                                 ▼
                         Published JSON Data
                                 ▲
                                 │
                         Web Data Publisher
                                 ▲
                                 │
                                dbt
                                 ▲
                                 │
                         SQL Server DWH
                                 ▲
                                 │
                              Airflow
                                 ▲
                                 │
                       External Job Sources
```

The main services run inside the same cloud environment:

```text
┌──────────────────────── Cloud VPS ─────────────────────────┐
│                                                           │
│   Docker Compose                                          │
│                                                           │
│   ┌───────────────┐      ┌─────────────────────────────┐  │
│   │ Apache Airflow│─────►│ SQL Server JobMarketDWH     │  │
│   └───────────────┘      └─────────────────────────────┘  │
│           │                                               │
│           │                ┌────────────────────────────┐ │
│           └───────────────►│ PostgreSQL                 │ │
│                            │ Airflow Metadata           │ │
│                            └────────────────────────────┘ │
│                                                           │
│   ┌───────────────┐      ┌─────────────────────────────┐  │
│   │      dbt      │─────►│ Analytical Marts            │  │
│   └───────────────┘      └─────────────────────────────┘  │
│                                                           │
│   ┌───────────────┐      ┌─────────────────────────────┐  │
│   │   Publisher   │─────►│ Next.js                     │  │
│   └───────────────┘      │ Career Radar                │  │
│                          └─────────────────────────────┘  │
│                                      │                    │
│                                      ▼                    │
│                                    Caddy                  │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

This allows the complete pipeline to operate independently of a developer workstation.

---

# Data Sources

Career Radar currently integrates **seven source families** through dedicated adapters.

| Source | Integration Strategy |
|---|---|
| Jooble | Job Search API |
| Lever | Lever-hosted company career sites |
| Akbank Career | First-party career API |
| Greenhouse | Greenhouse-hosted career boards |
| Workday | Workday-hosted career platform |
| SmartRecruiters | SmartRecruiters-hosted career sites |
| Workable | Published job descriptions from the Oredata and Vertigo Games boards, filtered for Türkiye |

### Canonical Job Distribution — November 7, 2026

| Source | Canonical Jobs |
|---|---:|
| Jooble | 297 |
| Lever | 258 |
| SmartRecruiters | 75 |
| Workday | 42 |
| Akbank | 36 |
| Greenhouse | 28 |
| Workable | 26 |
| **Total** | **762** |

The architecture intentionally uses **source-specific adapters** while enforcing a shared downstream staging contract.

This means a new source can be introduced without redesigning the analytical warehouse.

---

# Collection Strategy

Not all sources are treated equally.

First-party career sources and ATS platforms provide relatively direct market observations and can be collected frequently.

Aggregator APIs such as Jooble are useful for market breadth but may have stricter API quotas and different duplication characteristics.

For this reason, Career Radar uses separate orchestration strategies.

## Multi-Source Daily Pipeline

The primary source pipeline runs every day at:

```text
08:00
14:00
20:00
```

Timezone:

```text
Europe/Istanbul
```

The pipeline currently collects from:

```text
Akbank
Lever
Greenhouse
Workday
SmartRecruiters
Workable
```

## Jooble Pipeline

Jooble runs separately using a quota-aware schedule:

```text
Tuesday  09:00
Friday   09:00
```

This prevents unnecessary API consumption while still adding broader market discovery.

---

# End-to-End Data Pipeline

## 1. Source Collection

Python collectors communicate with source APIs and ATS platforms.

Each source adapter is responsible for understanding its external contract.

Collectors preserve source-specific information rather than forcing all APIs directly into the warehouse model.

---

## 2. RAW Layer

Raw source records are preserved before analytical transformation.

This provides:

- source lineage
- reproducibility
- debugging support
- historical evidence
- protection against upstream schema differences

The RAW layer represents **what the external source returned**.

---

## 3. Standardized Staging

Source-specific structures are transformed into a common job-posting contract.

Typical standardized attributes include:

```text
SourceSystem
SourcePlatform
SourceJobID
JobTitle
Company
Location
Description
EmploymentType
WorkModel
SourceTimestamp
ExtractionTimestamp
SearchKeyword
RawSourceFile
```

This staging contract isolates downstream logic from differences between external APIs.

---

# Canonical Job vs. Job Observation

One of the most important modeling decisions in Career Radar is separating a **job posting** from an **observation of that posting**.

A source-level vacancy is identified using:

```text
(SourceSystem, SourceJobID)
```

## Canonical Job

`FactJobPosting` represents the unique source-level vacancy.

If the same Lever job is collected twenty times, it is still one canonical job.

## Job Observation

`FactJobObservation` represents an individual observation of that vacancy by the ingestion system.

For example:

```text
Job A
│
├── Observed Monday 08:00
├── Observed Monday 14:00
├── Observed Monday 20:00
├── Observed Tuesday 08:00
└── Observed Tuesday 14:00
```

becomes:

```text
1 Canonical Job
5 Job Observations
```

This prevents repeated collection from artificially inflating vacancy counts while preserving historical market state.

Each observation references the raw posting captured during collection. The historical publisher uses that stored title and description when calculating weekly demand.

This model supports both:

- current-state market intelligence
- historical demand analysis

---

# Job Classification

External job titles are noisy and inconsistent.

A title such as:

```text
Senior Data Software Engineer / Airflow, Snowflake, AI, dbt
```

cannot be used directly as a reliable analytical dimension.

Career Radar therefore derives a structured classification:

```text
IsTechRole   = Tech
Career Area  = Data & Analytics
Role         = Data Engineer
Seniority    = Senior
```

The classification layer derives:

- Tech / Non-Tech status
- Career Area
- normalized Role
- Seniority

Classification logic follows a **precision-first approach** and is driven by configuration rather than hardcoded reporting logic.

---

# Career Area Taxonomy

Technology jobs are currently organized into eight high-level career areas:

1. Data & Analytics
2. AI & Machine Learning
3. Software Engineering
4. Cloud, DevOps & Platform
5. Cybersecurity
6. Enterprise Applications
7. IT Operations & Support
8. Other Tech

These areas create a stable analytical layer above inconsistent source titles.

Normalized roles sit below Career Area, followed by Seniority.

Conceptually:

```text
Technology Market
       │
       ▼
  Career Area
       │
       ▼
      Role
       │
       ▼
   Seniority
```

---

# Technology Intelligence

Career Radar analyzes job descriptions using a configuration-driven technology taxonomy.

The November 7 production snapshot contains **100 observed technologies**.

Examples include:

```text
Python
SQL
Java
.NET
AWS
Azure
GCP
Databricks
Spark
Airflow
dbt
Docker
Kubernetes
Terraform
Kafka
Salesforce
SAP
```

Technology extraction enables analysis such as:

- overall technology demand
- role-specific technology demand
- seniority-specific demand
- company technology stacks
- technology co-occurrence
- historical technology trends
- market breadth

The technology-pair table ranks pairs by shared postings. Support is the share of postings containing both technologies. Directional confidence measures how often one technology appears among postings containing the other. Lift compares observed co-occurrence with the expected frequency under independence. [Live technology pairs](https://techcareerradar.com/#technology-pairs)

---

# Capability Intelligence

Technologies answer:

> **Which tools appear in the market?**

Capabilities answer:

> **What are employers expecting professionals to be able to do?**

A Data Engineer posting may mention Airflow and describe responsibility for building data pipelines. The technology taxonomy records Airflow. The capability rules use the responsibility and role context to identify Data Pipeline Engineering.

## Capability Taxonomy

The production taxonomy has **29 capabilities** across **7 categories**. The catalog is versioned separately from the extraction context rules.

Current capabilities include:

```text
Data Pipeline Engineering
ETL/ELT Development
Data Modeling
Data Warehouse Engineering
Data Transformation
Data Workflow Automation
Data Product Development
Data Analysis
AI/ML Engineering
AI Workflow Engineering
RAG & Retrieval Engineering
Model Deployment & Monitoring
Data Quality & Validation
Application Development
Backend Development
Frontend Development
Mobile Application Development
API Development & Integration
Software Architecture & System Design
Distributed Systems Engineering
Cloud Infrastructure Engineering
Infrastructure Automation
CI/CD & Release Engineering
Monitoring & Observability
Incident Management
Performance & Scalability Engineering
Testing & Quality Engineering
Security Engineering
Troubleshooting & Technical Support
```

Capability extraction combines textual evidence with job context.

For example:

```text
"data pipelines"
        +
Role = Data Engineer
        +
Career Area = Data & Analytics
        │
        ▼
Data Pipeline Engineering
```

Context-aware extraction helps reduce false positives caused by:

- company descriptions
- generic terminology
- ambiguous keywords
- terminology with different meanings across roles

The three latest capabilities require explicit evidence in a relevant role. For example, an instruction to build a RAG pipeline can qualify. A general mention of RAG or a preference-only section is excluded by the pilot rules. [Capability taxonomy](config/capability_taxonomy.json) · [Role context](config/capability_context.json)

---

# Data Warehouse

Career Radar uses a dimensional **Microsoft SQL Server** warehouse.

The model separates reusable dimensions, canonical vacancies, historical observations, and many-to-many intelligence relationships.

## Core Dimensions

```text
DimCompany
DimLocation
DimCareerArea
DimRole
DimSkill
DimCapability
```

## Core Facts

```text
FactJobPosting
FactJobObservation
```

## Bridges

```text
BridgeJobPostingSkill
BridgeJobPostingCapability
```

Conceptually:

```text
                     DimCompany
                         │
                         │
DimLocation ───── FactJobPosting ───── DimRole
                         │
                         │
                   DimCareerArea
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
 BridgeJobPostingSkill     BridgeJobPostingCapability
            │                         │
            ▼                         ▼
        DimSkill                 DimCapability

FactJobPosting
      │
      ▼
FactJobObservation
```

---

# Analytics Engineering with dbt

dbt transforms warehouse data into analytics-ready marts.

Current production marts include:

## `mart_skill_demand`

Measures overall technology demand.

## `mart_role_skill_demand`

Measures technology demand within normalized roles.

## `mart_company_tech_stack`

Provides a market view of technologies appearing across companies.

## `mart_source_quality`

Monitors ingestion and source coverage.

## `mart_skill_trend`

Tracks daily observed technology demand using the warehouse skill relationships. The public weekly trend separately reprocesses the raw text associated with each observation.

## `mart_career_area_overview`

Provides aggregated intelligence across technology career areas.

## `mart_role_seniority_demand`

Measures market demand across normalized roles and seniority levels.

## `mart_role_capability_demand`

Measures capability demand within normalized technology roles.

## `mart_technology_stack_pairs`

Measures co-occurrence across source-level postings and calculates support, confidence in each direction, and lift. Tests cover pair uniqueness, pair ordering, count consistency, percentage bounds, and non-null metrics.

dbt is also used as a data-quality layer.

Production builds validate:

- relationships
- accepted values
- uniqueness
- non-null assumptions
- model-level integrity
- taxonomy relationships

The November 7 release passed **22 Python tests** and a full dbt build with **15 models and 103 data tests**. Run the Python suite from the repository root with `python -m unittest discover -s tests`. Run `dbt build` from `dbt/jobmarket` against the configured SQL Server target.

---

# Airflow Orchestration

Apache Airflow orchestrates the complete production workflow.

## Primary Pipeline

```text
Akbank Collector ─────────► Akbank RAW Loader ───────────┐
Lever Collector ──────────► Lever RAW Loader ────────────┤
Greenhouse Collector ─────► Greenhouse RAW Loader ───────┤
Workday Collector ─────────► Workday RAW Loader ─────────┤
SmartRecruiters Collector ─► SmartRecruiters RAW Loader ─┤
Workable Collector ─────────► Workable RAW Loader ────────┤
                                                         │
                                                         ▼
                                                Staging Transform
                                                         │
                                                         ▼
                                                     DWH Load
                                                         │
                                                         ▼
                                                Job Classification
                                                         │
                                                         ▼
                                             Capability Taxonomy Load
                                                         │
                                                         ▼
                                             Capability Extraction
                                                         │
                                                         ▼
                                              Capability DWH Load
                                                         │
                                                         ▼
                                                     dbt Build
                                                         │
                                                         ▼
                                                  Web Publisher
```

## Jooble Pipeline

```text
Jooble Collector
       │
       ▼
Jooble RAW Loader
       │
       ▼
Staging Transform
       │
       ▼
DWH Load
       │
       ▼
Job Classification
       │
       ▼
Capability Taxonomy
       │
       ▼
Capability Extraction
       │
       ▼
Capability DWH Load
       │
       ▼
dbt Build
       │
       ▼
Web Publisher
```

Airflow metadata is stored in PostgreSQL separately from the analytical SQL Server warehouse.

---

# Serving Layer

The public web application does **not** query the analytical SQL Server database directly.

Instead:

```text
SQL Server
    │
    ▼
   dbt
    │
    ▼
Analytical Marts
    │
    ▼
Python Publisher ◄──── Stored posting observations for weekly trends
    │
    ▼
Curated JSON
    │
    ▼
Next.js
```

The publisher exports curated datasets such as:

```text
metadata.json
skill-demand.json
role-skill-demand.json
company-tech-stack.json
skill-trend.json
technology-stack-pairs.json
role-capability-demand.json
source-quality.json
career-intelligence.json
```

This creates a clear boundary between:

- analytical storage
- analytical transformation
- serving
- presentation

and avoids exposing the warehouse directly to the public web application.

---

# Career Radar Web Application

The public product layer is built using:

```text
Next.js
TypeScript
Tailwind CSS
```

The application exposes technology demand, capability demand, technology pairs, role profiles, and weekly market trends. It reads the published JSON on request, so a successful scheduled publish refreshes the data without a web image rebuild. [Live application](https://techcareerradar.com/)

## Role Profiles

The Data Engineer and AI Engineer cards use the latest stored observation for each posting seen in the last 30 days. By default, the cards show postings with evidence of a Türkiye location or remote work from Türkiye. The sample selector also exposes all source records for comparison. Technology and capability counts include the number of identified employers. [Live role profiles](https://techcareerradar.com/#role-profiles)

### Role sample audit

The audit distinguishes a Türkiye location, remote work from Türkiye, a country label supplied only by an aggregator, a location outside Türkiye, and unclear location evidence. The Türkiye sample uses the first two categories. Explicit relocation to a recognized foreign destination can override a source label.

The audit groups records with the same posting title and URL after removing known tracking parameters. It also groups an aggregator listing with a single direct posting when the title and location are compatible and at least two substantive excerpts match. When employer identity is unavailable, a specific title is also required. Possible duplicates stay in the sample and appear in the audit counts. The role cards report the source mix and how many eligible postings contain capability evidence or a strong contextual match. The weekly market trend keeps its source-level counting rules. [Role audit implementation](ingestion/publishers/role_posting_audit.py)

## Recently Seen Employer Postings

The role opportunity cards show Türkiye-eligible Data Engineer and AI Engineer postings that were present in the latest validated employer-board snapshot and observed on at least two distinct days in a ten-day window. The count uses stored extraction dates in the Europe/Istanbul timezone. Repeated collection within a day contributes one observation day.

The pilot uses Lever, Greenhouse, Workable, and Workday. A newer empty or incomplete snapshot does not bring back vacancies from an older snapshot. Cards expire 48 hours after the board check and link to the original posting. The cards expose detected signals and source timestamps alongside the day count. Use the employer page to verify application status and deadlines. [Opportunity publisher](ingestion/publishers/role_opportunities.py)

## Weekly Market Trends

Weekly cohorts use Monday starts in the Europe/Istanbul timezone.

- **Observed that week** counts a posting once per week and uses its latest stored title and description in that week.
- **First seen that week** counts a posting in its first observed week and uses its first stored title and description. The opening week includes the inventory captured when collection began.

The selected signal's share uses the number of postings in the selected cohort as its denominator. The chart exposes the underlying counts, source coverage, and observation days. It starts with the first retained observations on October 16, 2026, and refreshes whenever the pipeline publishes a new snapshot. Historical text is evaluated with the current role classification and extraction rules. The same vacancy may appear in multiple sources, and changes in source coverage can affect comparisons. [Live trends](https://techcareerradar.com/#market-trends) · [Published dataset](https://techcareerradar.com/data/career-intelligence.json) · [History builder](ingestion/publishers/career_intelligence.py)

The product direction is:

> **Understand the market. Understand your next move.**

---

# Internal Analytics

A Streamlit-based analytical interface is also included in the repository for exploratory analysis and internal market inspection.

It can be used for:

- market KPIs
- technology demand
- role analysis
- technology trends
- company technology stacks
- source-quality analysis

The Next.js application is the primary direction for the public Career Radar product.

---

# Engineering Decisions

## 1. Source-Specific Adapters

Each external platform has its own collector.

Downstream processing operates on a common staging contract.

This reduces coupling between external APIs and the analytical warehouse.

---

## 2. Posting vs. Observation

Repeated collection does not create duplicate canonical jobs.

Instead:

```text
Canonical Job = identity
Observation   = historical evidence
```

This is essential for meaningful trend analysis.

---

## 3. Configuration-Driven Taxonomies

Role, seniority, technology, and capability definitions are maintained separately from core pipeline logic.

This makes taxonomy behavior easier to:

- profile
- test
- validate
- version
- extend

---

## 4. Market Evidence Before Recommendations

Career Radar does not begin with hardcoded career recommendations.

The system first builds evidence from:

```text
Role Demand
Seniority Demand
Technology Demand
Capability Demand
Company Breadth
Source Breadth
Historical Observations
```

Personalized recommendations will be built on top of this evidence layer.

---

## 5. Analytical Warehouse Is Not the Web Backend

SQL Server is intentionally isolated from the public web application.

Curated analytical results are published into a dedicated serving layer.

This keeps the web application simple and reduces direct coupling to the warehouse.

---

## 6. Separate Market Evidence from Learning Evidence

Future career recommendations will distinguish between:

### Market Evidence

What employers currently request.

### Learning Evidence

How a professional should learn those technologies and in what order.

This prevents job-posting frequency from being incorrectly interpreted as a complete learning roadmap.

---

# Technology Stack

| Layer | Technologies |
|---|---|
| Source Collection | Python, Requests |
| Text Processing | Python, Regex, BeautifulSoup |
| Warehouse | Microsoft SQL Server |
| Data Modeling | Dimensional Modeling |
| Analytics Engineering | dbt |
| Orchestration | Apache Airflow |
| Airflow Metadata | PostgreSQL |
| Infrastructure | Docker, Docker Compose |
| Cloud Runtime | Ubuntu Linux VPS |
| Reverse Proxy | Caddy |
| Internal Analytics | Streamlit, Plotly |
| Public Product | Next.js, TypeScript, Tailwind CSS |
| Version Control | Git, GitHub |

---

# Repository Structure

```text
JobMarket-Intelligence/
│
├── airflow/
│   └── dags/
│       └── Airflow orchestration
│
├── config/
│   └── Role, skill and capability taxonomies
│
├── dashboard/
│   └── Streamlit analytical application
│
├── data/
│   ├── raw/
│   └── sample/
│
├── dbt/
│   └── jobmarket/
│       └── dbt models, marts and tests
│
├── docs/
│   ├── architecture/
│   └── data_model/
│
├── ingestion/
│   ├── collectors/
│   │   └── Source-specific collection adapters
│   │
│   ├── loaders/
│   │   └── RAW, staging and DWH loaders
│   │
│   ├── parsers/
│   │   └── Classification and intelligence extraction
│   │
│   └── publishers/
│       └── Serving-layer publishers
│
├── sql/
│   ├── staging/
│   └── dwh/
│
├── tests/
│
├── web/
│   └── Next.js Career Radar application
│
├── Dockerfile.airflow
├── Dockerfile.web
├── docker-compose.yml
└── README.md
```

---

# Environment & Secrets

Runtime configuration is provided through environment variables.

Sensitive values such as:

```text
API keys
database passwords
Airflow secrets
```

are stored outside version control.

The repository includes environment configuration patterns without committing production credentials.

The production `.env` file is excluded from Git.

---

# Production Security Model

The cloud deployment follows a minimal public-exposure model.

Public-facing services:

```text
HTTP / HTTPS
SSH
```

Internal infrastructure such as:

```text
SQL Server
Airflow Webserver
PostgreSQL
```

is not intentionally exposed directly to the public internet.

Administrative Airflow access can be reached through an SSH tunnel instead of opening the Airflow port publicly.

---

# Data Quality

Data quality is enforced at multiple layers.

## Source Layer

Collectors validate source responses and preserve raw evidence.

## Staging Layer

Source-specific structures are normalized into a shared contract.

## Warehouse Layer

Canonical identity prevents repeated observations from becoming duplicate jobs.

## Classification Layer

Taxonomies are profiled against real market data before being frozen.

## Analytics Layer

dbt tests validate warehouse and mart assumptions.

The overall philosophy is:

> **Profile first. Freeze the taxonomy second. Automate third.**

---

# Current Production Lifecycle

A normal production cycle looks like:

```text
External Sources
       │
       ▼
Scheduled Airflow Run
       │
       ▼
Collect New Observations
       │
       ▼
Standardize
       │
       ▼
Resolve Canonical Jobs
       │
       ▼
Classify Roles
       │
       ▼
Extract Technologies
       │
       ▼
Extract Capabilities
       │
       ▼
Update Warehouse
       │
       ▼
Build dbt Marts
       │
       ▼
Publish Web Data
       │
       ▼
Career Radar Updated
```

No developer workstation is required for normal scheduled execution.

---

# Career Intelligence Model

The analytical hierarchy is evolving toward:

```text
Raw Job Posting
       │
       ▼
Is Tech Role?
       │
       ▼
Career Area
       │
       ▼
Role
       │
       ▼
Seniority
       │
       ├──────────────► Technologies
       │
       ├──────────────► Capabilities
       │
       ├──────────────► Professional Skills
       │
       └──────────────► Responsibilities
```

The first five layers plus Technology and Capability Intelligence are already implemented.

Professional Skills and richer responsibility intelligence belong to the next product phases.

---

# Career Recommendation Vision

The future Career Radar experience is designed around a simple flow:

```text
Select Career Area
        │
        ▼
Select Target Role
        │
        ▼
Select Seniority
        │
        ▼
Select Technologies You Already Know
        │
        ▼
     Career Radar
```

The system will compare a user's profile with observed market evidence.

Potential outputs include:

```text
Market Fit Score
Strong Areas
Technology Gaps
Capability Gaps
Emerging Skills
Recommended Next Technologies
Recommended Learning Path
```

A recommendation should eventually combine signals such as:

```text
Role Demand
×
Seniority Relevance
×
Skill Gap
×
Market Breadth
×
Learning Prerequisite Fit
```

Future versions can also incorporate:

```text
Demand Momentum
Company Breadth
Independent Source Breadth
Technology Co-occurrence
Capability Relevance
```

The recommendation layer is intentionally **not yet treated as a completed production feature**.

The current system is building the market evidence required to support it.

---

# Product Evolution

Career Radar is intended to evolve from market analytics into a persistent career intelligence product.

A future user journey may look like:

```text
Career Radar
     │
     ▼
My Career Profile
     │
     ▼
Market Fit Score
     │
     ▼
Skill Gaps
     │
     ▼
Learning Plan
     │
     ▼
Market Changes
     │
     ▼
Progress
     │
     └──────────────► Updated Market Fit
```

Potential future product features include:

- My Career Radar
- Since Your Last Visit
- What Should I Learn Next?
- Career Watchlist
- Career Trajectory
- Weekly Career Brief
- Market Strengths
- Skill Gap Tracking
- Learning Progress

---

# Roadmap

## Phase 1 — Multi-Source Market Foundation

- [x] Jooble ingestion
- [x] Lever ingestion
- [x] Akbank ingestion
- [x] Greenhouse ingestion
- [x] Workday ingestion
- [x] SmartRecruiters ingestion
- [x] Workable ingestion for Oredata and Vertigo Games
- [x] Standardized staging contract
- [x] Canonical job model
- [x] Historical observation model

## Phase 2 — Career Classification

- [x] Tech / Non-Tech classification
- [x] Career Area taxonomy
- [x] Normalized Role taxonomy
- [x] Seniority classification
- [x] Warehouse integration

## Phase 3 — Technology Intelligence

- [x] Technology taxonomy
- [x] Job ↔ Technology relationships
- [x] Technology demand marts
- [x] Role-specific demand
- [x] Company technology stacks
- [x] Technology co-occurrence mart and public pair table
- [x] Weekly technology demand from stored observations

## Phase 4 — Capability Intelligence

- [x] Capability taxonomy
- [x] Context-aware capability extraction
- [x] Explicit evidence rules for RAG, model deployment and monitoring, and data quality
- [x] Weekly capability demand from stored observations
- [x] `DimCapability`
- [x] `BridgeJobPostingCapability`
- [x] Role-capability demand mart
- [x] Airflow integration
- [x] Web publishing integration

## Phase 5 — Cloud Production

- [x] Cloud VPS
- [x] Dockerized SQL Server
- [x] Dockerized Airflow
- [x] PostgreSQL Airflow metadata
- [x] Cloud dbt execution
- [x] Automated web publisher
- [x] Dockerized Next.js
- [x] Caddy reverse proxy
- [x] Scheduled autonomous pipelines
- [x] Cloud Daily pipeline acceptance
- [x] Cloud Jooble pipeline acceptance
- [ ] Production executor hardening
- [ ] Reboot / recovery validation
- [x] Public domain and HTTPS
- [ ] Stronger collector failure semantics

## Phase 6 — Professional Skill Intelligence

- [ ] Professional Skill taxonomy
- [ ] Communication / collaboration signals
- [ ] Problem-solving signals
- [ ] Ownership / leadership signals
- [ ] Role-specific professional skill demand
- [ ] `mart_role_professional_skill_demand`

## Phase 7 — Recommendation Engine

- [x] Public Data Engineer and AI Engineer role profiles
- [ ] Personalized role profile model
- [ ] Skill-gap model
- [ ] Capability-gap model
- [ ] Market breadth scoring
- [ ] Demand momentum
- [ ] Recommendation scoring
- [ ] `mart_role_profile`
- [ ] `mart_career_recommendation`

## Phase 8 — Learning Evidence

- [ ] Learning source model
- [ ] Technology prerequisite graph
- [ ] Official documentation evidence
- [ ] Learning-path evidence
- [ ] `DimLearningSource`
- [ ] `FactLearningEvidence`
- [ ] `BridgeSkillPrerequisite`

## Phase 9 — Personalized Career Radar

- [ ] User profiles
- [ ] User skills
- [ ] Target roles
- [ ] Market Fit Score
- [ ] Personalized skill gaps
- [ ] Learning progress
- [ ] Career Watchlist
- [ ] Weekly Career Brief
- [ ] Market-change notifications

---

# Current Limitations

Career Radar is an evolving engineering and analytics product.

Current limitations include:

- the dataset is not intended to represent the entire Turkish technology labor market
- source coverage differs across ATS platforms and companies
- job descriptions can contain ambiguous or incomplete technology signals
- taxonomy-based classification requires continuous profiling as the market changes
- capability extraction is rule/context driven rather than a complete semantic understanding system
- historical coverage begins from the project's collection period rather than representing long-term labor-market history
- personalized recommendation and learning layers are not yet production features
- the current cloud architecture intentionally favors simplicity over distributed infrastructure

These constraints are treated as explicit engineering trade-offs rather than hidden assumptions.

---

# Design Philosophy

Career Radar is intentionally built incrementally.

The project does not start by building a recommendation engine and then searching for evidence to support it.

Instead:

```text
Collect
   ↓
Standardize
   ↓
Model
   ↓
Classify
   ↓
Measure
   ↓
Validate
   ↓
Build Market Evidence
   ↓
Recommend
```

The objective is to make future career recommendations traceable back to real market observations.

---

# Long-Term Direction

Career Radar aims to connect three layers:

```text
MARKET
What are employers asking for?

        +

PROFILE
What does the professional already know?

        +

LEARNING
What is the highest-value next step?

        │
        ▼

CAREER INTELLIGENCE
```

The result should not simply be another job board.

The goal is a system that helps technology professionals understand:

> **Where am I now?**

> **Where does the market place me?**

> **What is changing?**

> **What should I learn next?**

---

## Project Principle

> **Don't just search for your next job. Understand your next move.**
