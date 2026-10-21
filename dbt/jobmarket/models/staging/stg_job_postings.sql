{{ config(
    materialized='view'
) }}


-- ============================================================
-- STAGING: JOB POSTINGS
--
-- Grain:
--     One row per canonical source-level job posting.
--
-- Purpose:
--     Enrich FactJobPosting with descriptive dimensions
--     required by downstream analytics and marts.
--
-- Classification:
--     Job Classification V4.2 results are persisted in
--     FactJobPosting and exposed here together with the
--     Career Area dimension.
-- ============================================================


WITH job_postings AS
(
    SELECT
         JobPostingKey
        ,SourceJobID
        ,SourceSystem

        ,CompanyKey
        ,LocationKey
        ,RoleKey
        ,CareerAreaKey

        ,JobTitle
        ,Seniority
        ,EmploymentType
        ,Salary
        ,JobLink

        ,SourceUpdatedAt
        ,FirstObservedAt
        ,LastObservedAt
        ,CreatedAt

        -- Classification V4.2
        ,IsTechRole
        ,ClassificationConfidence
        ,ClassificationVersion

    FROM {{ source('dwh', 'FactJobPosting') }}
),


companies AS
(
    SELECT
         CompanyKey
        ,CompanyName

    FROM {{ source('dwh', 'DimCompany') }}
),


locations AS
(
    SELECT
         LocationKey
        ,LocationName

    FROM {{ source('dwh', 'DimLocation') }}
),


roles AS
(
    SELECT
         RoleKey
        ,RoleName

    FROM {{ source('dwh', 'DimRole') }}
),


career_areas AS
(
    SELECT
         CareerAreaKey
        ,CareerAreaName

    FROM {{ source('dwh', 'DimCareerArea') }}
)


SELECT
     j.JobPostingKey
    ,j.SourceJobID
    ,j.SourceSystem

    ,j.CompanyKey
    ,c.CompanyName

    ,j.LocationKey
    ,l.LocationName

    ,j.RoleKey
    ,r.RoleName

    ,j.CareerAreaKey
    ,ca.CareerAreaName

    ,j.JobTitle
    ,j.Seniority
    ,j.EmploymentType
    ,j.Salary
    ,j.JobLink

    ,j.SourceUpdatedAt
    ,j.FirstObservedAt
    ,j.LastObservedAt
    ,j.CreatedAt

    -- Classification V4.2
    ,j.IsTechRole
    ,j.ClassificationConfidence
    ,j.ClassificationVersion

FROM job_postings j

LEFT JOIN companies c
    ON j.CompanyKey = c.CompanyKey

LEFT JOIN locations l
    ON j.LocationKey = l.LocationKey

LEFT JOIN roles r
    ON j.RoleKey = r.RoleKey

LEFT JOIN career_areas ca
    ON j.CareerAreaKey = ca.CareerAreaKey