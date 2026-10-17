with observations as
(
    select
        o.JobObservationKey,
        o.RawJobPostingID,
        o.JobPostingKey,
        o.SearchKeyword,
        o.SearchLocation,
        o.ObservedAt

    from {{ source('dwh', 'FactJobObservation') }} o
)

select *
from observations