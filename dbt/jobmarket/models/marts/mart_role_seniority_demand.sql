{{
    config(
        materialized='table'
    )
}}

WITH tech_jobs AS
(
    SELECT
         JobPostingKey
        ,CareerAreaName
        ,RoleName
        ,Seniority
        ,CompanyName
        ,SourceSystem
        ,FirstObservedAt
        ,LastObservedAt
    FROM {{ ref('stg_job_postings') }}
    WHERE IsTechRole = 'Tech'
),

role_seniority_metrics AS
(
    SELECT
         CareerAreaName
        ,RoleName
        ,Seniority
        ,COUNT(DISTINCT JobPostingKey) AS JobCount
        ,COUNT(DISTINCT CompanyName) AS CompanyCount
        ,COUNT(DISTINCT SourceSystem) AS SourceCount
        ,MIN(FirstObservedAt) AS FirstObservedAt
        ,MAX(LastObservedAt) AS LastObservedAt
    FROM tech_jobs
    GROUP BY
         CareerAreaName
        ,RoleName
        ,Seniority
),

role_totals AS
(
    SELECT
         CareerAreaName
        ,RoleName
        ,COUNT(DISTINCT JobPostingKey) AS RoleJobCount
    FROM tech_jobs
    GROUP BY
         CareerAreaName
        ,RoleName
),

career_area_totals AS
(
    SELECT
         CareerAreaName
        ,COUNT(DISTINCT JobPostingKey) AS CareerAreaJobCount
    FROM tech_jobs
    GROUP BY
         CareerAreaName
),

total_tech_jobs AS
(
    SELECT
        COUNT(DISTINCT JobPostingKey) AS TotalTechJobCount
    FROM tech_jobs
)

SELECT
     m.CareerAreaName
    ,m.RoleName
    ,m.Seniority
    ,m.JobCount
    ,m.CompanyCount
    ,m.SourceCount

    ,r.RoleJobCount
    ,c.CareerAreaJobCount
    ,t.TotalTechJobCount

    -- Seniority'nin kendi role ailesi içindeki payı.
    ,CAST(
        100.0 * m.JobCount
        / NULLIF(r.RoleJobCount, 0)
        AS DECIMAL(10, 2)
    ) AS SeniorityShareWithinRole

    -- Bu role + seniority kombinasyonunun
    -- Career Area içindeki payı.
    ,CAST(
        100.0 * m.JobCount
        / NULLIF(c.CareerAreaJobCount, 0)
        AS DECIMAL(10, 2)
    ) AS DemandShareWithinCareerArea

    -- Tüm Tech market içindeki payı.
    ,CAST(
        100.0 * m.JobCount
        / NULLIF(t.TotalTechJobCount, 0)
        AS DECIMAL(10, 2)
    ) AS TechMarketShare

    ,m.FirstObservedAt
    ,m.LastObservedAt

FROM role_seniority_metrics m

INNER JOIN role_totals r
    ON r.CareerAreaName = m.CareerAreaName
   AND r.RoleName = m.RoleName

INNER JOIN career_area_totals c
    ON c.CareerAreaName = m.CareerAreaName

CROSS JOIN total_tech_jobs t