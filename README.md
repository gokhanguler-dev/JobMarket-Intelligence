# JobMarket Intelligence

An end-to-end **data engineering and analytics platform** that transforms multi-source job postings into actionable insights about technology demand, role expectations, and emerging skills in Turkey's data job market.

The project is designed around a simple question:

> **What technologies are companies looking for, and what should a data professional learn next?**

---

## Why This Project?

Traditional job boards are designed to help users find individual vacancies.

**JobMarket Intelligence treats the job market as a dataset.**

The platform collects job postings from multiple sources, standardizes semi-structured data, builds an analytical warehouse, and transforms the results into market and career intelligence.

It aims to answer questions such as:

- Which technologies are most in demand?
- How do skill requirements differ across data roles?
- Which technology stacks appear across companies?
- How is skill demand changing over time?
- What should a data professional learn next?

---

## Architecture

```text
Job Sources
    │
    ▼
Python Collectors
    │
    ▼
RAW / Staging
    │
    ▼
SQL Server DWH
    │
    ▼
dbt
    │
    ▼
Analytical Marts
    │
    ▼
Apache Airflow
    │
    ├──────────────► Streamlit Analytics Dashboard
    │
    └──────────────► Next.js Public Web Application
```

The pipeline separates **data collection, standardization, warehouse modeling, analytics engineering, orchestration, and presentation** into independent layers.

---

## Current Data Snapshot

| Metric | Current Value |
|---|---:|
| Unique Job Postings | 346 |
| Companies | 75 |
| Skills Tracked | 32 |
| Data Sources | 3 |

> The dataset grows incrementally as scheduled ingestion pipelines collect new observations.

---

## Data Sources

The current pipeline integrates multiple job-posting sources using dedicated source adapters.

| Source | Integration |
|---|---|
| Jooble | API |
| Trendyol | Lever Postings API |
| Akbank Career | Career API |

Each source has its own collector and loader, while all sources eventually conform to a **common staging contract**.

This allows new sources to be introduced without redesigning the downstream warehouse.

---

## Data Pipeline

### 1. Multi-Source Ingestion

Python collectors retrieve job postings from multiple APIs and career platforms.

Raw responses are preserved before transformation, providing lineage between the original source data and the analytical warehouse.

### 2. Standardized Staging

Source-specific structures are normalized into a common job-posting model containing fields such as:

- source system and platform
- job identifier
- job title
- company
- location
- description
- employment and work model
- source timestamps
- extraction timestamps

### 3. Text Processing

Job descriptions are cleaned and analyzed to extract structured information from unstructured text.

The processing layer includes:

- HTML cleaning
- canonical skill extraction
- role classification
- seniority classification
- configurable skill and role taxonomies

### 4. Data Warehouse

The standardized data is loaded into a dimensional SQL Server warehouse.

A key modeling decision is separating a **job posting** from an **observation of that posting**.

This prevents repeated collection from being interpreted as new vacancies while still preserving historical observations.

---

## Data Model

### Dimensions

- `DimCompany`
- `DimLocation`
- `DimRole`
- `DimSkill`

### Facts

- `FactJobPosting`
- `FactJobObservation`

### Bridge

- `BridgeJobPostingSkill`

`FactJobPosting` represents a unique source-level vacancy using:

```text
(SourceSystem, SourceJobID)
```

`FactJobObservation` records when that vacancy was observed by the ingestion pipeline.

This design supports both current-state analytics and historical market analysis.

---

## Analytics Engineering with dbt

dbt transforms warehouse data into analytics-ready models.

Current analytical marts include:

### `mart_skill_demand`

Measures overall technology demand across job postings.

### `mart_role_skill_demand`

Measures skill demand within individual job roles.

### `mart_company_tech_stack`

Provides a view of technologies appearing across companies.

### `mart_skill_trend`

Tracks observed technology demand over time.

### `mart_source_quality`

Monitors ingestion quality and coverage across different sources.

dbt tests are used to validate model integrity and important data-quality assumptions.

---

## Orchestration

**Apache Airflow** orchestrates the end-to-end pipelines.

### Daily Pipeline

```text
Akbank Collector
       │
Akbank RAW Loader
       │
       ├──────────────┐
       │              │
Lever Collector       │
       │              │
Lever RAW Loader      │
       │              │
       └──────┬───────┘
              ▼
      Staging Transform
              │
              ▼
          DWH Load
              │
              ▼
          dbt Build
```

### Jooble Pipeline

Jooble ingestion runs separately with a **quota-aware collection strategy** to reduce unnecessary API consumption.

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
dbt Build
```

The local development environment uses Airflow with `SequentialExecutor`, intentionally keeping the infrastructure lightweight.

---

## Analytics Applications

### Streamlit Analytics Dashboard

A Streamlit application provides an internal analytics interface for exploring:

- market KPIs
- skill demand
- role distribution
- skill trends
- company technology stacks
- source quality

### Next.js Web Application

A separate **Next.js + TypeScript** application is being developed as the public-facing data product.

The goal is to provide an accessible interface for exploring market demand and eventually generating role-specific skill recommendations.

The public application is intentionally separated from the analytical warehouse rather than exposing SQL Server directly.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Ingestion | Python, Requests |
| Processing | Python, BeautifulSoup, Regex |
| Database | SQL Server |
| Data Modeling | Dimensional Modeling |
| Analytics Engineering | dbt |
| Orchestration | Apache Airflow |
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
├── config/                   # Skill and role taxonomies
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
│   └── parsers/              # Text and taxonomy processing
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

### Job Identity vs. Observation

A job posting and an observation of that job are modeled separately.

This allows the same vacancy to be collected repeatedly without inflating the number of unique jobs.

### Source-Specific Adapters

Each external source has its own ingestion adapter, but downstream processing operates on a standardized contract.

This reduces coupling between source APIs and the analytical model.

### Configuration-Driven Taxonomies

Skill and role definitions are maintained outside the processing logic, making classification rules easier to extend.

### Appropriate Technology Over Artificial Complexity

The current dataset does not require distributed processing technologies such as Spark or Kafka.

Rather than introducing them solely to increase the number of technologies in the stack, the project uses infrastructure appropriate for its current scale.

### Public Serving Isolation

The analytical SQL Server warehouse is not intended to be exposed directly to the public application.

Curated analytical outputs will instead be published to a dedicated serving layer for the public website.

---

## Roadmap

- [x] Multi-source job ingestion
- [x] Standardized staging layer
- [x] Text cleaning and skill extraction
- [x] Role classification
- [x] Dimensional SQL Server warehouse
- [x] Incremental DWH loading
- [x] dbt analytical models
- [x] Data quality tests
- [x] Airflow orchestration
- [x] Streamlit analytics dashboard
- [x] Next.js web application foundation
- [ ] Public analytics serving layer
- [ ] Dynamic web analytics
- [ ] Role and skill explorer
- [ ] Skill-gap recommendations
- [ ] Public cloud deployment

---

## Project Goal

The goal of this project is not simply to collect job postings.

It demonstrates how a modern data engineering workflow can transform fragmented and semi-structured job-market data into a reusable analytical product for understanding:

**technology demand, role expectations, market trends, and career skill gaps.**