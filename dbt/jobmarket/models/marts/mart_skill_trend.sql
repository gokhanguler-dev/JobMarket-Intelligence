with daily_jobs as
(
    select distinct
        cast(o.ObservedAt as date) as ObservationDate,
        o.JobPostingKey

    from {{ ref('stg_job_observations') }} o
),

daily_total_jobs as
(
    select
        ObservationDate,
        count(distinct JobPostingKey) as ObservedJobCount

    from daily_jobs

    group by
        ObservationDate
),

daily_skill_demand as
(
    select
        d.ObservationDate,
        s.SkillKey,
        s.SkillName,

        count(distinct d.JobPostingKey) as JobCount

    from daily_jobs d

    inner join {{ ref('stg_job_skills') }} s
        on s.JobPostingKey = d.JobPostingKey

    group by
        d.ObservationDate,
        s.SkillKey,
        s.SkillName
)

select
    d.ObservationDate,

    d.SkillKey,
    d.SkillName,

    d.JobCount,

    t.ObservedJobCount,

    cast(
        100.0 * d.JobCount
        / nullif(t.ObservedJobCount, 0)
        as decimal(10, 2)
    ) as DemandPercentage

from daily_skill_demand d

inner join daily_total_jobs t
    on t.ObservationDate = d.ObservationDate