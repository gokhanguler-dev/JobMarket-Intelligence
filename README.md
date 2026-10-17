\# JobMarket Intelligence



An end-to-end data engineering and analytics platform that transforms

job postings into actionable insights about technology demand,

role expectations, and emerging skills in Turkey's data job market.



\## Why This Project?



Job boards are designed to help people find individual vacancies.

JobMarket Intelligence looks at the market as a dataset.



It answers questions such as:



\- Which technologies are most in demand?

\- How do skill requirements differ across data roles?

\- Which technology stacks appear across companies?

\- How is skill demand changing over time?

\- What should a data professional learn next?



\## Architecture



Job Sources

&#x20;   ↓

Python Collectors

&#x20;   ↓

RAW / Staging

&#x20;   ↓

SQL Server DWH

&#x20;   ↓

dbt

&#x20;   ↓

Analytical Marts

&#x20;   ↓

Airflow

&#x20;   ↓

Analytics \& Web Application



\## Current Data Snapshot



| Metric | Value |

|---|---:|

| Unique Job Postings | 346 |

| Companies | 75 |

| Skills Tracked | 32 |

| Data Sources | 3 |



\## Data Sources



The current pipeline integrates multiple job-posting sources using

source-specific adapters:



\- Jooble

\- Lever / Trendyol

\- Akbank Career



Each source is normalized into a common staging contract before being

loaded into the analytical warehouse.



\## Data Model



The warehouse separates job identity from observations over time.



Core models include:



\- `FactJobPosting` — unique source-level job postings

\- `FactJobObservation` — individual observations of a job

\- `BridgeJobPostingSkill` — job-to-skill relationships

\- `DimCompany`

\- `DimLocation`

\- `DimRole`

\- `DimSkill`



This allows the platform to distinguish between a unique vacancy and

repeated observations of that vacancy.



\## Analytics Layer



dbt transforms the warehouse into analytics-ready marts:



\- `mart\_skill\_demand`

\- `mart\_role\_skill\_demand`

\- `mart\_company\_tech\_stack`

\- `mart\_skill\_trend`

\- `mart\_source\_quality`



These models power skill-demand analysis, role comparisons, company

technology profiles and source-quality monitoring.



\## Orchestration



Apache Airflow orchestrates the local development pipeline.



\### Daily Pipeline



Akbank + Lever  

→ RAW  

→ STG  

→ DWH  

→ dbt



\### Jooble Pipeline



Jooble is collected separately with a quota-aware schedule to reduce

unnecessary API usage.



\## Analytics Applications



\### Streamlit Analytics Dashboard



An internal analytics dashboard provides interactive exploration of:



\- market KPIs

\- skill demand

\- role distribution

\- skill trends

\- company technology stacks

\- source quality



\### Public Web Application



A Next.js application is currently being developed as the public-facing

data product.



The final application will provide interactive market intelligence and

skill recommendations without exposing the underlying SQL Server

warehouse.



\## Technology Stack



\*\*Data Engineering\*\*



Python · SQL Server · Docker · Apache Airflow



\*\*Analytics Engineering\*\*



dbt · dimensional modeling · data quality testing



\*\*Analytics \& Product\*\*



Streamlit · Plotly · Next.js · TypeScript · Tailwind CSS



\## Repository Structure



```text

JobMarket-Intelligence/

├── airflow/          # DAGs and orchestration

├── config/           # Source and taxonomy configuration

├── dashboard/        # Streamlit analytics application

├── dbt/              # dbt transformations and analytical marts

├── ingestion/

│   ├── collectors/   # Source adapters

│   ├── loaders/      # RAW, STG and DWH loaders

│   └── parsers/      # Text, skill and role parsing

├── sql/

│   ├── staging/

│   └── dwh/

├── tests/

├── web/              # Next.js public application

├── Dockerfile.airflow

└── docker-compose.yml

