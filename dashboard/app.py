import pandas as pd
import plotly.express as px
import streamlit as st

from db import run_query


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="JobMarket Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    [data-testid="stMetric"] {
        background-color: rgba(120, 120, 120, 0.06);
        border: 1px solid rgba(120, 120, 120, 0.18);
        padding: 18px;
        border-radius: 14px;
    }

    [data-testid="stMetricValue"] {
        font-size: 30px;
        font-weight: 700;
    }

    .insight-card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(120, 120, 120, 0.18);
        background-color: rgba(120, 120, 120, 0.05);
        min-height: 125px;
    }

    .insight-title {
        font-size: 14px;
        opacity: 0.7;
        margin-bottom: 8px;
    }

    .insight-value {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .insight-description {
        font-size: 13px;
        opacity: 0.75;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADERS
# ============================================================

@st.cache_data(ttl=600)
def load_overview():

    return run_query(
        """
        SELECT
            COUNT(*) AS TotalJobs,
            COUNT(DISTINCT CompanyKey) AS TotalCompanies,
            COUNT(DISTINCT SourceSystem) AS TotalSources,
            MAX(LastObservedAt) AS LastUpdated
        FROM dwh.FactJobPosting
        """
    )


@st.cache_data(ttl=600)
def load_skill_demand():

    return run_query(
        """
        SELECT
            SkillKey,
            SkillName,
            JobCount,
            CompanyCount,
            SourceCount,
            TotalJobCount,
            DemandPercentage
        FROM marts.mart_skill_demand
        ORDER BY JobCount DESC
        """
    )


@st.cache_data(ttl=600)
def load_role_skill_demand():

    return run_query(
        """
        SELECT
            RoleName,
            SkillKey,
            SkillName,
            JobCount,
            CompanyCount,
            SourceCount,
            RoleJobCount,
            RoleDemandPercentage
        FROM marts.mart_role_skill_demand
        ORDER BY RoleName, JobCount DESC
        """
    )


@st.cache_data(ttl=600)
def load_company_stack():

    return run_query(
        """
        SELECT
            CompanyName,
            SkillKey,
            SkillName,
            JobCount,
            RoleCount,
            SourceCount,
            FirstObservedAt,
            LastObservedAt
        FROM marts.mart_company_tech_stack
        ORDER BY JobCount DESC
        """
    )


@st.cache_data(ttl=600)
def load_source_quality():

    return run_query(
        """
        SELECT
            SourceSystem,
            JobCount,
            ObservationCount,
            JobsWithSkillCount,
            JobSkillPairCount,
            ClassifiedJobCount,
            JobsWithCompanyCount,
            SkillCoveragePercentage,
            RoleClassificationPercentage,
            CompanyCoveragePercentage,
            AvgObservationsPerJob
        FROM marts.mart_source_quality
        ORDER BY JobCount DESC
        """
    )


@st.cache_data(ttl=600)
def load_skill_trend():

    return run_query(
        """
        SELECT
            ObservationDate,
            SkillKey,
            SkillName,
            JobCount,
            ObservedJobCount,
            DemandPercentage
        FROM marts.mart_skill_trend
        ORDER BY ObservationDate, JobCount DESC
        """
    )


@st.cache_data(ttl=600)
def load_role_distribution():

    return run_query(
        """
        SELECT
            ISNULL(r.RoleName, 'Other') AS RoleName,
            COUNT(*) AS JobCount
        FROM dwh.FactJobPosting j
        LEFT JOIN dwh.DimRole r
            ON r.RoleKey = j.RoleKey
        GROUP BY
            ISNULL(r.RoleName, 'Other')
        ORDER BY
            JobCount DESC
        """
    )


# ============================================================
# LOAD DATA
# ============================================================

try:

    overview = load_overview()
    skill_demand = load_skill_demand()
    role_skill = load_role_skill_demand()
    company_stack = load_company_stack()
    source_quality = load_source_quality()
    skill_trend = load_skill_trend()
    role_distribution = load_role_distribution()

except Exception as error:

    st.error(
        f"Database connection failed: {error}"
    )

    st.stop()


# ============================================================
# OVERVIEW VALUES
# ============================================================

total_jobs = int(
    overview.iloc[0]["TotalJobs"]
)

total_companies = int(
    overview.iloc[0]["TotalCompanies"]
)

total_sources = int(
    overview.iloc[0]["TotalSources"]
)

total_skills = int(
    skill_demand["SkillKey"].nunique()
)

jobs_with_skill = int(
    source_quality["JobsWithSkillCount"]
    .fillna(0)
    .sum()
)

skill_coverage = (
    100 * jobs_with_skill / total_jobs
    if total_jobs
    else 0
)

last_updated = overview.iloc[0]["LastUpdated"]

if pd.notna(last_updated):

    last_updated = pd.to_datetime(
        last_updated
    ).strftime(
        "%d %b %Y • %H:%M"
    )

else:

    last_updated = "N/A"


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns(
    [4, 1]
)

with header_left:

    st.title(
        "JobMarket Intelligence"
    )

    st.markdown(
        """
        **Data & Analytics Skills in the Turkish Job Market**

        Turning job-posting data into actionable insights about
        technology demand, roles and company tech stacks.
        """
    )

with header_right:

    st.markdown(
        "##### Last Updated"
    )

    st.write(
        last_updated
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "Market Explorer"
)

st.sidebar.caption(
    "Explore technology demand across roles "
    "and companies."
)

role_options = sorted(
    role_skill["RoleName"]
    .dropna()
    .unique()
    .tolist()
)

selected_role = st.sidebar.selectbox(
    "Role",
    ["All Roles"] + role_options
)

top_n = st.sidebar.slider(
    "Number of skills",
    min_value=5,
    max_value=20,
    value=10,
    step=1
)

st.sidebar.divider()

st.sidebar.caption(
    "Sources"
)

for source in sorted(
    source_quality["SourceSystem"]
    .dropna()
    .tolist()
):

    st.sidebar.write(
        f"✓ {source}"
    )


# ============================================================
# KPI SECTION
# ============================================================

st.subheader(
    "Market Overview"
)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric(
    "Job Postings",
    f"{total_jobs:,}"
)

kpi2.metric(
    "Companies",
    f"{total_companies:,}"
)

kpi3.metric(
    "Skills Tracked",
    f"{total_skills:,}"
)

kpi4.metric(
    "Data Sources",
    f"{total_sources:,}"
)

kpi5.metric(
    "Skill Coverage",
    f"{skill_coverage:.1f}%"
)


# ============================================================
# MARKET INSIGHTS
# ============================================================

st.subheader(
    "Market Insights"
)

top_skill_row = (
    skill_demand
    .sort_values(
        "JobCount",
        ascending=False
    )
    .iloc[0]
)

top_skill = top_skill_row[
    "SkillName"
]

top_skill_jobs = int(
    top_skill_row[
        "JobCount"
    ]
)

classified_roles = (
    role_distribution[
        role_distribution[
            "RoleName"
        ] != "Other"
    ]
)

if not classified_roles.empty:

    top_role_row = (
        classified_roles
        .sort_values(
            "JobCount",
            ascending=False
        )
        .iloc[0]
    )

    top_role = top_role_row[
        "RoleName"
    ]

    top_role_jobs = int(
        top_role_row[
            "JobCount"
        ]
    )

else:

    top_role = "N/A"
    top_role_jobs = 0


best_source_row = (
    source_quality
    .sort_values(
        "SkillCoveragePercentage",
        ascending=False
    )
    .iloc[0]
)

best_source = best_source_row[
    "SourceSystem"
]

best_source_coverage = float(
    best_source_row[
        "SkillCoveragePercentage"
    ]
)


insight1, insight2, insight3 = st.columns(3)

with insight1:

    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">
                MOST IN-DEMAND SKILL
            </div>
            <div class="insight-value">
                {top_skill}
            </div>
            <div class="insight-description">
                Detected in {top_skill_jobs:,}
                unique job postings.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with insight2:

    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">
                LEADING CLASSIFIED ROLE
            </div>
            <div class="insight-value">
                {top_role}
            </div>
            <div class="insight-description">
                {top_role_jobs:,} unique postings
                classified into this role.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with insight3:

    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">
                HIGHEST SKILL COVERAGE SOURCE
            </div>
            <div class="insight-value">
                {best_source}
            </div>
            <div class="insight-description">
                {best_source_coverage:.1f}%
                of jobs contain a tracked skill.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.divider()


# ============================================================
# MOST IN-DEMAND SKILLS
# ============================================================

st.subheader(
    "Most In-Demand Skills"
)

if selected_role == "All Roles":

    chart_data = (
        skill_demand
        .sort_values(
            "JobCount",
            ascending=False
        )
        .head(top_n)
        .sort_values(
            "JobCount",
            ascending=True
        )
    )

    chart_title = (
        "Top Skills Across All Roles"
    )

else:

    chart_data = (
        role_skill[
            role_skill["RoleName"]
            == selected_role
        ]
        .sort_values(
            "JobCount",
            ascending=False
        )
        .head(top_n)
        .sort_values(
            "JobCount",
            ascending=True
        )
    )

    chart_title = (
        f"Top Skills for {selected_role}"
    )


fig_skills = px.bar(
    chart_data,
    x="JobCount",
    y="SkillName",
    orientation="h",
    text="JobCount",
    title=chart_title,
    labels={
        "JobCount": "Job Postings",
        "SkillName": "Skill"
    },
)

fig_skills.update_traces(
    textposition="outside"
)

fig_skills.update_layout(
    height=520,
    title_x=0,
    margin=dict(
        l=20,
        r=50,
        t=60,
        b=20
    ),
    yaxis_title=None,
    xaxis_title="Unique Job Postings",
    showlegend=False,
)

st.plotly_chart(
    fig_skills,
    use_container_width=True
)


# ============================================================
# DEMAND + ROLE DISTRIBUTION
# ============================================================

left_column, right_column = st.columns(2)


with left_column:

    st.subheader(
        "Skill Demand"
    )

    demand_data = (
        skill_demand
        .sort_values(
            "DemandPercentage",
            ascending=False
        )
        .head(10)
        .sort_values(
            "DemandPercentage",
            ascending=True
        )
    )

    fig_demand = px.bar(
        demand_data,
        x="DemandPercentage",
        y="SkillName",
        orientation="h",
        text="DemandPercentage",
        labels={
            "DemandPercentage":
                "Demand (%)",
            "SkillName":
                "Skill"
        },
    )

    fig_demand.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside"
    )

    fig_demand.update_layout(
        height=460,
        margin=dict(
            l=10,
            r=40,
            t=20,
            b=20
        ),
        yaxis_title=None,
        xaxis_title=(
            "Share of Job Postings (%)"
        ),
        showlegend=False,
    )

    st.plotly_chart(
        fig_demand,
        use_container_width=True
    )


with right_column:

    st.subheader(
        "Jobs by Role"
    )

    role_chart = (
        role_distribution
        .sort_values(
            "JobCount",
            ascending=False
        )
        .sort_values(
            "JobCount",
            ascending=True
        )
    )

    fig_roles = px.bar(
        role_chart,
        x="JobCount",
        y="RoleName",
        orientation="h",
        text="JobCount",
        labels={
            "RoleName": "Role",
            "JobCount": "Job Postings"
        },
    )

    fig_roles.update_traces(
        textposition="outside"
    )

    fig_roles.update_layout(
        height=460,
        margin=dict(
            l=10,
            r=40,
            t=20,
            b=20
        ),
        yaxis_title=None,
        xaxis_title="Unique Job Postings",
        showlegend=False,
    )

    st.plotly_chart(
        fig_roles,
        use_container_width=True
    )


st.divider()


# ============================================================
# SKILL TREND
# ============================================================

st.subheader(
    "Skill Demand Over Time"
)

st.caption(
    "Demand observed across job-posting snapshots "
    "collected by the ingestion pipeline."
)

available_skills = (
    skill_demand
    .sort_values(
        "JobCount",
        ascending=False
    )["SkillName"]
    .head(15)
    .tolist()
)

default_skills = (
    available_skills[:4]
)

selected_skills = st.multiselect(
    "Compare skills",
    options=available_skills,
    default=default_skills
)

trend_filtered = skill_trend[
    skill_trend["SkillName"]
    .isin(selected_skills)
].copy()


if not trend_filtered.empty:

    trend_filtered[
        "ObservationDate"
    ] = pd.to_datetime(
        trend_filtered[
            "ObservationDate"
        ]
    )

    fig_trend = px.line(
        trend_filtered,
        x="ObservationDate",
        y="DemandPercentage",
        color="SkillName",
        markers=True,
        labels={
            "ObservationDate":
                "Observation Date",
            "DemandPercentage":
                "Demand (%)",
            "SkillName":
                "Skill"
        },
    )

    fig_trend.update_layout(
        height=480,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),
        xaxis_title=None,
        yaxis_title="Demand (%)",
        legend_title_text="Skill",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_trend,
        use_container_width=True
    )

else:

    st.info(
        "Select at least one skill "
        "to display the trend."
    )


st.divider()


# ============================================================
# COMPANY TECH STACK
# ============================================================

st.subheader(
    "Company Tech Stack"
)

st.caption(
    "Explore which technologies appear most frequently "
    "in each company's observed job postings."
)

company_options = (
    company_stack[
        "CompanyName"
    ]
    .dropna()
    .value_counts()
    .index
    .tolist()
)

if company_options:

    selected_company = st.selectbox(
        "Select company",
        company_options
    )

    company_filtered = (
        company_stack[
            company_stack[
                "CompanyName"
            ]
            == selected_company
        ]
        .sort_values(
            "JobCount",
            ascending=False
        )
    )

    company_chart = (
        company_filtered
        .head(15)
        .sort_values(
            "JobCount",
            ascending=True
        )
    )

    fig_company = px.bar(
        company_chart,
        x="JobCount",
        y="SkillName",
        orientation="h",
        text="JobCount",
        labels={
            "JobCount":
                "Job Postings",
            "SkillName":
                "Technology"
        },
    )

    fig_company.update_traces(
        textposition="outside"
    )

    fig_company.update_layout(
        height=460,
        margin=dict(
            l=20,
            r=50,
            t=20,
            b=20
        ),
        yaxis_title=None,
        xaxis_title="Job Postings",
        showlegend=False,
    )

    st.plotly_chart(
        fig_company,
        use_container_width=True
    )

else:

    st.info(
        "No company tech-stack data available."
    )


st.divider()


# ============================================================
# SOURCE QUALITY
# ============================================================

st.subheader(
    "Source Quality & Coverage"
)

st.caption(
    "Comparison of skill extraction, role classification "
    "and company coverage across ingestion sources."
)

source_chart = source_quality[
    [
        "SourceSystem",
        "SkillCoveragePercentage",
        "RoleClassificationPercentage",
        "CompanyCoveragePercentage"
    ]
].copy()

source_chart = source_chart.rename(
    columns={
        "SkillCoveragePercentage":
            "Skill Coverage",
        "RoleClassificationPercentage":
            "Role Classification",
        "CompanyCoveragePercentage":
            "Company Coverage"
    }
)

source_chart_long = source_chart.melt(
    id_vars="SourceSystem",
    var_name="Metric",
    value_name="Coverage"
)

fig_source = px.bar(
    source_chart_long,
    x="SourceSystem",
    y="Coverage",
    color="Metric",
    barmode="group",
    text_auto=".1f",
    labels={
        "SourceSystem": "Source",
        "Coverage": "Coverage (%)"
    },
)

fig_source.update_layout(
    height=460,
    margin=dict(
        l=20,
        r=20,
        t=20,
        b=20
    ),
    xaxis_title=None,
    yaxis_title="Coverage (%)",
    legend_title_text=None,
)

st.plotly_chart(
    fig_source,
    use_container_width=True
)


with st.expander(
    "View source quality details"
):

    source_display = source_quality[
        [
            "SourceSystem",
            "JobCount",
            "ObservationCount",
            "JobsWithSkillCount",
            "JobSkillPairCount",
            "SkillCoveragePercentage",
            "RoleClassificationPercentage",
            "CompanyCoveragePercentage",
            "AvgObservationsPerJob"
        ]
    ].copy()

    source_display.columns = [
        "Source",
        "Jobs",
        "Observations",
        "Jobs With Skills",
        "Job-Skill Pairs",
        "Skill Coverage (%)",
        "Role Classification (%)",
        "Company Coverage (%)",
        "Avg. Observations / Job"
    ]

    st.dataframe(
        source_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ABOUT
# ============================================================

st.divider()

with st.expander(
    "About this project"
):

    st.markdown(
        """
        **JobMarket Intelligence** is an end-to-end
        data engineering and analytics project.

        Job postings are collected from multiple sources,
        standardized through a staging layer, modeled in
        SQL Server, transformed into analytical marts with
        dbt and orchestrated with Apache Airflow.

        **Pipeline**

        `Job Sources → Python → RAW → STG → DWH → dbt → Streamlit`

        **Technology Stack**

        Python · SQL Server · Docker · Apache Airflow ·
        dbt · Streamlit · Plotly
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "JobMarket Intelligence  •  "
    "Python  •  SQL Server  •  dbt  •  "
    "Apache Airflow  •  Streamlit"
)