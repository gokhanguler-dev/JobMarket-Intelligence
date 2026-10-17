with job_skills as
(
    select
        b.JobPostingKey,
        b.SkillKey,
        s.SkillName

    from {{ source('dwh', 'BridgeJobPostingSkill') }} b

    inner join {{ source('dwh', 'DimSkill') }} s
        on s.SkillKey = b.SkillKey
)

select *
from job_skills