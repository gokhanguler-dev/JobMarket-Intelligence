USE JobMarketDWH;
GO


/* ============================================================
   DIM COMPANY
   ============================================================ */

INSERT INTO dwh.DimCompany
(
    CompanyName
)
SELECT DISTINCT
    LTRIM(RTRIM(s.Company))
FROM stg.JobPosting s
WHERE NULLIF(LTRIM(RTRIM(s.Company)), '') IS NOT NULL
  AND NOT EXISTS
  (
      SELECT 1
      FROM dwh.DimCompany d
      WHERE d.CompanyName = LTRIM(RTRIM(s.Company))
  );


/* ============================================================
   DIM LOCATION
   ============================================================ */

INSERT INTO dwh.DimLocation
(
    LocationName
)
SELECT DISTINCT
    LTRIM(RTRIM(s.JobLocation))
FROM stg.JobPosting s
WHERE NULLIF(LTRIM(RTRIM(s.JobLocation)), '') IS NOT NULL
  AND NOT EXISTS
  (
      SELECT 1
      FROM dwh.DimLocation d
      WHERE d.LocationName = LTRIM(RTRIM(s.JobLocation))
  );


/* ============================================================
   DIM ROLE
   ============================================================ */

INSERT INTO dwh.DimRole
(
    RoleName
)
SELECT DISTINCT
    LTRIM(RTRIM(s.NormalizedRole))
FROM stg.JobPosting s
WHERE NULLIF(LTRIM(RTRIM(s.NormalizedRole)), '') IS NOT NULL
  AND NOT EXISTS
  (
      SELECT 1
      FROM dwh.DimRole d
      WHERE d.RoleName = LTRIM(RTRIM(s.NormalizedRole))
  );


/* ============================================================
   DIM SKILL
   ============================================================ */

INSERT INTO dwh.DimSkill
(
    SkillName
)
SELECT DISTINCT
    LTRIM(RTRIM(s.SkillName))
FROM stg.JobPostingSkill s
WHERE NULLIF(LTRIM(RTRIM(s.SkillName)), '') IS NOT NULL
  AND NOT EXISTS
  (
      SELECT 1
      FROM dwh.DimSkill d
      WHERE d.SkillName = LTRIM(RTRIM(s.SkillName))
  );
GO