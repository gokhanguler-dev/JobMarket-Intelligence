with role_totals as
(
    select
        RoleName,
        count(distinct JobPostingKey) as RoleJobCount

    from {{ ref('stg_job_postings') }}

    group by
        RoleName
),

role_skill_demand as
(
    select
        RoleName,
        SkillKey,
        SkillName,

        count(distinct JobPostingKey) as JobCount,

        count(distinct CompanyName) as CompanyCount,

        count(distinct SourceSystem) as SourceCount

    from {{ ref('int_job_skills') }}

    group by
        RoleName,
        SkillKey,
        SkillName
)

select
    d.RoleName,
    d.SkillKey,
    d.SkillName,

    d.JobCount,
    d.CompanyCount,
    d.SourceCount,

    r.RoleJobCount,

    cast(
        100.0 * d.JobCount
        / nullif(r.RoleJobCount, 0)
        as decimal(10, 2)
    ) as RoleDemandPercentage

from role_skill_demand d

inner join role_totals r
    on r.RoleName = d.RoleName