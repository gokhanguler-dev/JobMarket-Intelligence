USE JobMarketDWH;
GO

/* ============================================================
   BRIDGE JOB POSTING SKILL

   Grain:
   1 row = 1 unique JobPosting + 1 unique Skill

   STG tarafında aynı SourceJobID farklı observation'larda
   tekrar bulunabileceği için DISTINCT uygulanır.
   ============================================================ */

INSERT INTO dwh.BridgeJobPostingSkill
(
    JobPostingKey,
    SkillKey
)

SELECT DISTINCT
    f.JobPostingKey,
    ds.SkillKey

FROM stg.JobPostingSkill s

INNER JOIN stg.JobPosting jp
    ON jp.JobPostingStgID = s.JobPostingStgID

INNER JOIN dwh.FactJobPosting f
    ON  f.SourceSystem = jp.SourceSystem
    AND f.SourceJobID = jp.SourceJobID

INNER JOIN dwh.DimSkill ds
    ON ds.SkillName = LTRIM(RTRIM(s.SkillName))

WHERE NOT EXISTS
(
    SELECT 1
    FROM dwh.BridgeJobPostingSkill b
    WHERE b.JobPostingKey = f.JobPostingKey
      AND b.SkillKey = ds.SkillKey
);
GO