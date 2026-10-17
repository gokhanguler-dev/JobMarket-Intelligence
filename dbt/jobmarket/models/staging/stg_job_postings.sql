with job_postings as
(
    select
        f.JobPostingKey,
        f.SourceSystem,
        f.SourceJobID,

        f.CompanyKey,
        c.CompanyName,

        f.LocationKey,
        l.LocationName,

        f.RoleKey,
        r.RoleName,

        f.JobTitle,
        f.Seniority,
        f.EmploymentType,
        f.Salary,
        f.JobLink,

        f.SourceUpdatedAt,
        f.FirstObservedAt,
        f.LastObservedAt

    from {{ source('dwh', 'FactJobPosting') }} f

    left join {{ source('dwh', 'DimCompany') }} c
        on c.CompanyKey = f.CompanyKey

    left join {{ source('dwh', 'DimLocation') }} l
        on l.LocationKey = f.LocationKey

    left join {{ source('dwh', 'DimRole') }} r
        on r.RoleKey = f.RoleKey
)

select *
from job_postings