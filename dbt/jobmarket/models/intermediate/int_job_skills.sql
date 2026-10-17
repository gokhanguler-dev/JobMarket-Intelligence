with job_skills as
(
    select
        j.JobPostingKey,
        j.SourceSystem,
        j.SourceJobID,

        j.JobTitle,
        j.CompanyName,
        j.LocationName,
        j.RoleName,
        j.Seniority,
        j.EmploymentType,

        j.FirstObservedAt,
        j.LastObservedAt,

        s.SkillKey,
        s.SkillName

    from {{ ref('stg_job_postings') }} j

    inner join {{ ref('stg_job_skills') }} s
        on s.JobPostingKey = j.JobPostingKey
)

select *
from job_skills