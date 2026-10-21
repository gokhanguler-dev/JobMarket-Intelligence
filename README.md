# JobMarket Intelligence

An end-to-end **data engineering and career intelligence platform** that transforms multi-source technology job postings into structured market intelligence about roles, technologies, capabilities, seniority, and employer demand.

The project is built around a simple question:

> **What does the technology job market expect, and what should a technology professional learn next?**

---

## Why This Project?

Traditional job boards are designed to help users find individual vacancies.

**JobMarket Intelligence treats the job market as a dataset.**

The platform continuously collects job postings from multiple sources, standardizes semi-structured data, builds an analytical warehouse, classifies technology roles, extracts market signals, and transforms those signals into career intelligence.

The project aims to answer questions such as:

- Which technology career areas are hiring?
- Which roles are most in demand?
- Which technologies are requested most frequently?
- How do technology requirements differ across roles and seniority levels?
- What capabilities do employers expect beyond individual tools?
- Which technology stacks commonly appear together?
- How is technology demand changing over time?
- What should a technology professional learn next?

The long-term product direction is a **Career Radar** that combines market evidence with a user's existing skills to identify career fit, skill gaps, and recommended next learning steps.

---

## Current Data Snapshot

| Metric | Current Value |
|---|---:|
| Unique Job Postings | 531 |
| Companies | 78 |
| Classified Tech Jobs | 273 |
| Observed Technologies | 93 |
| Data Sources | 3 |
| Capability Definitions | 26 |
| Capability Categories | 7 |

> The dataset grows incrementally as scheduled ingestion pipelines collect new observations.

---

## Architecture

```text
                    JOB SOURCES
                         │
              ┌──────────┼──────────┐
              │          │          │
            Jooble      Lever     Akbank
              │          │          │
              └──────────┼──────────┘
                         ▼
                 Python Collectors
                         │
                         ▼
                   RAW / Staging
                         │
                         ▼
                 SQL Server DWH
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
   Job Classification  Skill        Capability
                       Extraction    Extraction
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                        dbt
                         │
                         ▼
                 Analytical Marts
                         │
                         ▼
                  Serving Layer
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          Streamlit              Next.js
          Analytics              Public Web
```

**Apache Airflow** orchestrates the ingestion, transformation, classification, warehouse loading, analytics, and publishing workflows.

The architecture separates:

- data collection
- source standardization
- warehouse modeling
- job classification
- technology extraction
- capability extraction
- analytics engineering
- orchestration
- serving and presentation

into independent layers.

---

## Data Sources

The pipeline currently integrates job postings using dedicated source adapters.

| Source | Integration |
|---|---|
| Jooble | Job Search API |
| Lever-hosted company career sites | Lever Postings API |
| Akbank Career | Career API |

Lever ingestion is configuration-driven and can collect postings from multiple company career sites without changing downstream processing logic.

Each source ultimately conforms to a **common staging contract**, allowing additional sources to be introduced without redesigning the warehouse.

---

## Data Pipeline

### 1. Multi-Source Ingestion

Python collectors retrieve job postings from APIs and company career platforms.

Raw responses are preserved before transformation, providing lineage between source data and analytical warehouse records.

### 2. Standardized Staging

Source-specific structures are normalized into a common job-posting contract containing fields such as:

- source system
- source platform
- source job identifier
- job title
- company
- location
- description
- employment type
- work model
- source timestamps
- extraction timestamp
- discovery keyword
- raw source file

This isolates downstream models from differences between external APIs.

### 3. Job Classification

Raw job titles are not reliable analytical dimensions.

For example, a title such as:

```text
Senior Data Software Engineer / Airflow, Snowflake, AI, dbt
```

can be transformed into structured dimensions:

```text
IsTechRole   = Tech
Career Area  = Data & Analytics
Role         = Data Engineer
Seniority    = Senior
```

The classification pipeline derives:

- Tech / Non-Tech status
- Career Area
- normalized Role
- Seniority

Classification rules are configuration-driven and follow a **precision-first approach**.

---

## Career Area Taxonomy

Technology jobs are currently organized into the following high-level career areas:

1. Data & Analytics
2. AI & Machine Learning
3. Software Engineering
4. Cloud, DevOps & Platform
5. Cybersecurity
6. Enterprise Applications
7. IT Operations & Support
8. Other Tech

This creates a stable analytical layer above inconsistent source job titles.

---

## Technology Intelligence

Job descriptions are analyzed using a configuration-driven technology taxonomy.

The current taxonomy supports more than 100 technology definitions, with **93 technologies currently observed** in collected market data.

Examples include:

```text
Python
SQL
AWS
Azure
GCP
Databricks
Spark
Terraform
Docker
Kubernetes
Airflow
dbt
.NET
Java
Salesforce
SAP
```

Technology extraction enables analysis such as:

- overall technology demand
- role-specific technology demand
- company technology stacks
- technology co-occurrence
- technology trends over time

---

## Capability Intelligence

Knowing which technologies appear in a job posting does not fully describe what employers expect candidates to **do**.

For example:

```text
Technology Signals
------------------
Airflow
Terraform
AWS
GitHub Actions
Spark
```

may correspond to capabilities such as:

```text
Data Pipeline Engineering
Data Workflow Automation
Infrastructure Automation
Cloud Infrastructure Engineering
CI/CD & Release Engineering
```

The project therefore includes an additional **Capability Intelligence** layer.

Capability Taxonomy V1 currently contains:

- **26 capabilities**
- **7 capability categories**

Current capability areas include:

- Data Pipeline Engineering
- ETL/ELT Development
- Data Modeling
- Data Warehouse Engineering
- Data Transformation
- Data Workflow Automation
- Data Product Development
- Data Analysis
- AI/ML Engineering
- AI Workflow Engineering
- Application Development
- Backend Development
- Frontend Development
- Mobile Application Development
- API Development & Integration
- Software Architecture & System Design
- Distributed Systems Engineering
- Cloud Infrastructure Engineering
- Infrastructure Automation
- CI/CD & Release Engineering
- Monitoring & Observability
- Incident Management
- Performance & Scalability Engineering
- Testing & Quality Engineering
- Security Engineering
- Troubleshooting & Technical Support

Capability extraction combines textual evidence with job context.

For example:

```text
"data pipelines"
        +
Role = Data Engineer
        +
Career Area = Data & Analytics
        ↓
Data Pipeline Engineering
```

This context-aware approach helps reduce false positives caused by company descriptions, generic text, and terminology that has different meanings across roles.

> **Capability Taxonomy V1 is currently under active profiling and validation before being promoted into the production warehouse model.**

---

## Data Warehouse

Standardized data is loaded into a dimensional **SQL Server** warehouse.

### Core Dimensions

- `DimCompany`
- `DimLocation`
- `DimRole`
- `DimSkill`
- `DimCareerArea`

### Core Facts

- `FactJobPosting`
- `FactJobObservation`

### Bridges

- `BridgeJobPostingSkill`

The capability model is currently being prepared for:

- `DimCapability`
- `BridgeJobPostingCapability`

---

## Job Identity vs. Observation

One of the key modeling decisions is separating a **job posting** from an **observation of that posting**.

A unique source-level vacancy is identified using:

```text
(SourceSystem, SourceJobID)
```

`FactJobPosting` represents the canonical vacancy.

`FactJobObservation` records when that vacancy was observed by the ingestion pipeline.

This prevents repeated collection from being interpreted as new vacancies while still preserving historical market observations.

The model therefore supports both:

- current-state market analytics
- historical market analysis

---

## Analytics Engineering with dbt

dbt transforms warehouse data into analytics-ready models.

Current analytical marts include:

### `mart_skill_demand`

Measures overall technology demand across job postings.

### `mart_role_skill_demand`

Measures technology demand within individual job roles.

### `mart_company_tech_stack`

Provides a view of technologies appearing across companies.

### `mart_skill_trend`

Tracks observed technology demand over time.

### `mart_source_quality`

Monitors ingestion quality and coverage across different sources.

### `mart_career_area_overview`

Provides market-level analytics across technology career areas.

### `mart_role_seniority_demand`

Measures demand across normalized roles and seniority levels.

dbt tests validate model integrity and important data-quality assumptions.

Planned career-intelligence marts include:

```text
mart_role_capability_demand
mart_role_professional_skill_demand
mart_role_profile
mart_career_recommendation
```

---

## Orchestration

**Apache Airflow** orchestrates the end-to-end data workflows.

### Daily Pipeline

```text
Akbank Collector ──► Akbank RAW Loader ──┐
                                         │
Lever Collector ───► Lever RAW Loader ───┤
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
                                     dbt Build
                                         │
                                         ▼
                                  Web Publishing
```

### Jooble Pipeline

Jooble ingestion runs separately using a **quota-aware collection strategy**.

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
dbt Build
```

The local development environment uses Airflow with `SequentialExecutor`, keeping infrastructure appropriate for the current workload.

Airflow metadata is stored in PostgreSQL separately from the analytical SQL Server warehouse.

---

## Analytics Applications

### Streamlit Analytics Dashboard

The Streamlit application provides an internal analytical interface for exploring:

- market KPIs
- technology demand
- role distribution
- technology trends
- company technology stacks
- source quality

### Next.js Public Web Application

A separate **Next.js + TypeScript** application provides the foundation for the public-facing data product.

The public web layer is intentionally isolated from the analytical SQL Server warehouse.

Curated analytical outputs are published into a dedicated serving format rather than exposing SQL Server directly.

---

## Career Radar

The long-term product layer is designed around a simple user flow:

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

The system will combine market evidence with the user's current profile to estimate:

```text
Market Fit
Strong Areas
Technology Gaps
Capability Gaps
Emerging Skills
Recommended Next Technologies
Recommended Learning Path
```

Recommendations are intended to be **evidence-based rather than hardcoded**.

A future recommendation can be supported by signals such as:

- demand within the target role
- seniority relevance
- number of companies requesting the technology
- number of independent sources
- technology co-occurrence
- capability relevance
- demand momentum
- prerequisite relationships

The product direction can be summarized as:

> **Don't just search for your next job. Understand your next move.**

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Ingestion | Python, Requests |
| Text Processing | Python, BeautifulSoup, Regex |
| Database | SQL Server |
| Data Modeling | Dimensional Modeling |
| Analytics Engineering | dbt |
| Orchestration | Apache Airflow |
| Airflow Metadata | PostgreSQL |
| Infrastructure | Docker, Docker Compose |
| Internal Analytics | Streamlit, Plotly |
| Public Web | Next.js, TypeScript, Tailwind CSS |
| Version Control | Git, GitHub |

---

## Repository Structure

```text
JobMarket-Intelligence/
│
├── airflow/
│   └── dags/                 # Airflow orchestration
│
├── config/                   # Role, skill and capability taxonomies
│
├── dashboard/                # Streamlit analytics dashboard
│
├── data/
│   ├── raw/                  # Local raw source data
│   └── sample/
│
├── dbt/
│   └── jobmarket/            # dbt project and analytical marts
│
├── docs/
│   ├── architecture/
│   └── data_model/
│
├── ingestion/
│   ├── collectors/           # Source-specific collectors
│   ├── loaders/              # RAW, STG and DWH loaders
│   ├── parsers/              # Classification and text processing
│   └── publishers/           # Serving-layer publishers
│
├── sql/
│   ├── staging/
│   └── dwh/
│
├── tests/
│
├── web/                      # Next.js public application
│
├── Dockerfile.airflow
├── docker-compose.yml
└── README.md
```

---

## Engineering Decisions

### Source-Specific Adapters

Each external source has its own ingestion adapter while downstream processing operates on a standardized contract.

This reduces coupling between external APIs and the analytical model.

### Configuration-Driven Taxonomies

Role, seniority, technology, and capability definitions are maintained outside the core processing logic.

This makes classification behavior easier to profile, validate, and extend.

### Precision Before Coverage

Classification and capability extraction prioritize reliable evidence over artificially maximizing coverage.

Ambiguous evidence is profiled and validated before being promoted into production rules.

### Historical Observation Model

Job identity and job observation are modeled separately, allowing repeated collection without inflating unique vacancy counts.

### Appropriate Technology Over Artificial Complexity

The current workload does not require distributed processing technologies such as Spark or Kafka.

Rather than introducing technologies solely to increase stack complexity, infrastructure is selected according to the actual scale and requirements of the project.

### Public Serving Isolation

The SQL Server analytical warehouse is not intended to be exposed directly to the public application.

Curated outputs are published into a separate serving layer for the website.

---

## Roadmap

### Data Platform

- [x] Multi-source job ingestion
- [x] Standardized staging layer
- [x] SQL Server dimensional warehouse
- [x] Incremental DWH loading
- [x] Job observation history
- [x] Apache Airflow orchestration
- [x] dbt analytical models
- [x] Data-quality tests

### Career Intelligence

- [x] Tech / Non-Tech classification
- [x] Career Area taxonomy
- [x] Role normalization
- [x] Seniority classification
- [x] Technology Taxonomy V2
- [x] Technology demand marts
- [x] Role and seniority demand mart
- [ ] Capability Taxonomy V1 production model
- [ ] Professional Skills taxonomy
- [ ] Role capability demand mart
- [ ] Career recommendation marts
- [ ] Learning evidence model

### Product

- [x] Streamlit analytics dashboard
- [x] Next.js public web foundation
- [x] DWH-to-web publishing pipeline
- [ ] Dynamic Career Area explorer
- [ ] Role and technology explorer
- [ ] Career Radar
- [ ] Skill-gap recommendation engine
- [ ] Learning-path recommendations
- [ ] Public cloud deployment

---

## Project Goal

The goal of **JobMarket Intelligence** is not simply to collect job postings.

It demonstrates how a modern data engineering workflow can transform fragmented and semi-structured labor-market data into a reusable **career intelligence product**.

The platform is evolving toward four layers of market understanding:

```text
What role is this?
        │
        ▼
What technologies does it require?
        │
        ▼
What must someone actually be capable of doing?
        │
        ▼
What should they learn next?
```

Ultimately, the project aims to turn job-market data into transparent, evidence-based intelligence about:

**career areas, role demand, technology demand, capabilities, market trends, skill gaps, and career development.**