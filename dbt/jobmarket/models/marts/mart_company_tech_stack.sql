with company_skill_demand as
(
    select
        CompanyName,
        SkillKey,
        SkillName,

        count(distinct JobPostingKey) as JobCount,

        count(distinct RoleName) as RoleCount,

        count(distinct SourceSystem) as SourceCount,

        min(FirstObservedAt) as FirstObservedAt,
        max(LastObservedAt) as LastObservedAt

    from {{ ref('int_job_skills') }}

    where CompanyName is not null

    group by
        CompanyName,
        SkillKey,
        SkillName
)

select
    CompanyName,
    SkillKey,
    SkillName,
    JobCount,
    RoleCount,
    SourceCount,
    FirstObservedAt,
    LastObservedAt

from company_skill_demand