
{{ config(materialized='table') }}

with job_skills as
(
    select distinct
        JobPostingKey,
        SkillKey,
        SkillName
    from {{ ref('int_job_skills') }}
),

skill_counts as
(
    select
        SkillKey,
        count(*) as SkillJobCount
    from job_skills
    group by SkillKey
),

pair_counts as
(
    select
        a.SkillKey as SkillKey1,
        b.SkillKey as SkillKey2,
        count(*) as BothJobs
    from job_skills a
    inner join job_skills b
        on a.JobPostingKey = b.JobPostingKey
       and a.SkillKey < b.SkillKey
    group by
        a.SkillKey,
        b.SkillKey
),

total_jobs as
(
    select
        count(*) as TotalJobs
    from {{ ref('stg_job_postings') }}
)

select
    p.SkillKey1,
    p.SkillKey2,

    s1.SkillName as Skill1,
    s2.SkillName as Skill2,

    p.BothJobs,

    c1.SkillJobCount as Skill1Jobs,
    c2.SkillJobCount as Skill2Jobs,

    t.TotalJobs,

    cast(
        100.0 * p.BothJobs
        / nullif(t.TotalJobs, 0)
        as decimal(10, 2)
    ) as SupportPct,

    cast(
        100.0 * p.BothJobs
        / nullif(c1.SkillJobCount, 0)
        as decimal(10, 2)
    ) as Confidence1To2Pct,

    cast(
        100.0 * p.BothJobs
        / nullif(c2.SkillJobCount, 0)
        as decimal(10, 2)
    ) as Confidence2To1Pct,

    cast(
        1.0 * p.BothJobs * t.TotalJobs
        / nullif(
            1.0 * c1.SkillJobCount * c2.SkillJobCount,
            0
        )
        as decimal(10, 2)
    ) as Lift

from pair_counts p

inner join skill_counts c1
    on p.SkillKey1 = c1.SkillKey

inner join skill_counts c2
    on p.SkillKey2 = c2.SkillKey

inner join
(
    select distinct
        SkillKey,
        SkillName
    from job_skills
) s1
    on p.SkillKey1 = s1.SkillKey

inner join
(
    select distinct
        SkillKey,
        SkillName
    from job_skills
) s2
    on p.SkillKey2 = s2.SkillKey

cross join total_jobs t
