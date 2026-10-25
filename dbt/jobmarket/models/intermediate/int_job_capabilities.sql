with job_capabilities as
(
    select
        f.JobPostingKey,
        f.SourceSystem,
        f.SourceJobID,

        f.CareerAreaKey,
        ca.CareerAreaName,

        f.RoleKey,
        r.RoleName,

        f.Seniority,

        f.CompanyKey,
        c.CompanyName,

        bc.CapabilityKey,
        cap.CapabilityName,
        cap.CapabilityCategory,

        bc.Confidence

    from {{ source('dwh', 'FactJobPosting') }} f

    inner join {{ source('dwh', 'BridgeJobPostingCapability') }} bc
        on bc.JobPostingKey = f.JobPostingKey

    inner join {{ source('dwh', 'DimCapability') }} cap
        on cap.CapabilityKey = bc.CapabilityKey

    inner join {{ source('dwh', 'DimCareerArea') }} ca
        on ca.CareerAreaKey = f.CareerAreaKey

    inner join {{ source('dwh', 'DimRole') }} r
        on r.RoleKey = f.RoleKey

    inner join {{ source('dwh', 'DimCompany') }} c
        on c.CompanyKey = f.CompanyKey

    where f.IsTechRole = 'Tech'
)

select *
from job_capabilities