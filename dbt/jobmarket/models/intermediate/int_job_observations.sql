with observation_summary as
(
    select
        j.JobPostingKey,
        j.SourceSystem,
        j.SourceJobID,
        j.JobTitle,
        j.CompanyName,
        j.RoleName,

        count(o.JobObservationKey) as ObservationCount,

        min(o.ObservedAt) as FirstObservationAt,
        max(o.ObservedAt) as LastObservationAt

    from {{ ref('stg_job_postings') }} j

    left join {{ ref('stg_job_observations') }} o
        on o.JobPostingKey = j.JobPostingKey

    group by
        j.JobPostingKey,
        j.SourceSystem,
        j.SourceJobID,
        j.JobTitle,
        j.CompanyName,
        j.RoleName
)

select *
from observation_summary