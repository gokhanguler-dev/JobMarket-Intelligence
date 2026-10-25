with capability_demand as
(
    select
        CareerAreaName,
        RoleName,
        Seniority,
        CapabilityCategory,
        CapabilityName,

        count(distinct JobPostingKey) as CapabilityJobCount,
        count(distinct CompanyKey) as CompanyCount,
        count(distinct SourceSystem) as SourceCount

    from {{ ref('int_job_capabilities') }}

    group by
        CareerAreaName,
        RoleName,
        Seniority,
        CapabilityCategory,
        CapabilityName
),

role_seniority_market as
(
    select
        CareerAreaName,
        RoleName,
        Seniority,
        JobCount as RoleSeniorityJobCount

    from {{ ref('mart_role_seniority_demand') }}
)

select
    cd.CareerAreaName,
    cd.RoleName,
    cd.Seniority,

    cd.CapabilityCategory,
    cd.CapabilityName,

    cd.CapabilityJobCount,
    cd.CompanyCount,
    cd.SourceCount,

    rsm.RoleSeniorityJobCount,

    cast(
        100.0 * cd.CapabilityJobCount
        / nullif(rsm.RoleSeniorityJobCount, 0)
        as decimal(10, 2)
    ) as CapabilityDemandPercentage

from capability_demand cd

inner join role_seniority_market rsm
    on  rsm.CareerAreaName = cd.CareerAreaName
    and rsm.RoleName = cd.RoleName
    and rsm.Seniority = cd.Seniority