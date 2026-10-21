with tech_jobs as
(
    select
        JobPostingKey,
        CompanyName,
        SourceSystem,
        CareerAreaName,
        ClassificationConfidence,
        FirstObservedAt,
        LastObservedAt

    from {{ ref('stg_job_postings') }}

    where IsTechRole = 'Tech'
),

career_area_metrics as
(
    select
        CareerAreaName,

        count(
            distinct JobPostingKey
        ) as JobCount,

        count(
            distinct CompanyName
        ) as CompanyCount,

        count(
            distinct SourceSystem
        ) as SourceCount,

        count(
            distinct case
                when ClassificationConfidence = 'High'
                then JobPostingKey
            end
        ) as HighConfidenceJobCount,

        count(
            distinct case
                when ClassificationConfidence = 'Medium'
                then JobPostingKey
            end
        ) as MediumConfidenceJobCount,

        count(
            distinct case
                when ClassificationConfidence = 'Low'
                then JobPostingKey
            end
        ) as LowConfidenceJobCount,

        min(
            FirstObservedAt
        ) as FirstObservedAt,

        max(
            LastObservedAt
        ) as LastObservedAt

    from tech_jobs

    group by
        CareerAreaName
),

total_tech_jobs as
(
    select
        count(
            distinct JobPostingKey
        ) as TotalTechJobCount

    from tech_jobs
)

select
    c.CareerAreaName,

    c.JobCount,
    c.CompanyCount,
    c.SourceCount,

    c.HighConfidenceJobCount,
    c.MediumConfidenceJobCount,
    c.LowConfidenceJobCount,

    t.TotalTechJobCount,

    cast(
        100.0 * c.JobCount
        / nullif(t.TotalTechJobCount, 0)
        as decimal(10, 2)
    ) as JobSharePercentage,

    c.FirstObservedAt,
    c.LastObservedAt

from career_area_metrics c

cross join total_tech_jobs t