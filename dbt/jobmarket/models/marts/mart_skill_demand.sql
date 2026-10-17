with skill_demand as
(
    select
        SkillKey,
        SkillName,

        count(distinct JobPostingKey) as JobCount,

        count(
            distinct CompanyName
        ) as CompanyCount,

        count(
            distinct SourceSystem
        ) as SourceCount

    from {{ ref('int_job_skills') }}

    group by
        SkillKey,
        SkillName
),

total_jobs as
(
    select
        count(*) as TotalJobCount

    from {{ ref('stg_job_postings') }}
)

select
    s.SkillKey,
    s.SkillName,

    s.JobCount,
    s.CompanyCount,
    s.SourceCount,

    t.TotalJobCount,

    cast(
        100.0 * s.JobCount
        / nullif(t.TotalJobCount, 0)
        as decimal(10, 2)
    ) as DemandPercentage

from skill_demand s

cross join total_jobs t