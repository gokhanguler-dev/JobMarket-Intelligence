with job_quality as
(
    select
        SourceSystem,

        count(*) as JobCount,

        sum(
            case
                when RoleName <> 'Other' then 1
                else 0
            end
        ) as ClassifiedJobCount,

        sum(
            case
                when CompanyName is not null then 1
                else 0
            end
        ) as JobsWithCompanyCount

    from {{ ref('stg_job_postings') }}

    group by
        SourceSystem
),

skill_quality as
(
    select
        SourceSystem,

        count(
            distinct JobPostingKey
        ) as JobsWithSkillCount,

        count(*) as JobSkillPairCount

    from {{ ref('int_job_skills') }}

    group by
        SourceSystem
),

observation_quality as
(
    select
        SourceSystem,

        sum(ObservationCount) as ObservationCount,

        avg(
            cast(
                ObservationCount as decimal(18, 2)
            )
        ) as AvgObservationsPerJob

    from {{ ref('int_job_observations') }}

    group by
        SourceSystem
)

select
    j.SourceSystem,

    j.JobCount,

    o.ObservationCount,

    s.JobsWithSkillCount,

    s.JobSkillPairCount,

    j.ClassifiedJobCount,

    j.JobsWithCompanyCount,

    cast(
        100.0 * s.JobsWithSkillCount
        / nullif(j.JobCount, 0)
        as decimal(10, 2)
    ) as SkillCoveragePercentage,

    cast(
        100.0 * j.ClassifiedJobCount
        / nullif(j.JobCount, 0)
        as decimal(10, 2)
    ) as RoleClassificationPercentage,

    cast(
        100.0 * j.JobsWithCompanyCount
        / nullif(j.JobCount, 0)
        as decimal(10, 2)
    ) as CompanyCoveragePercentage,

    cast(
        o.AvgObservationsPerJob
        as decimal(10, 2)
    ) as AvgObservationsPerJob

from job_quality j

left join skill_quality s
    on s.SourceSystem = j.SourceSystem

left join observation_quality o
    on o.SourceSystem = j.SourceSystem