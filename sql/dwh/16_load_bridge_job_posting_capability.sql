/* ============================================================
   16_load_bridge_job_posting_capability.sql

   Purpose:
       Load accepted Capability Taxonomy V1.2 relationships
       from staging into the DWH bridge table.

   Source:
       stg.JobPostingCapability

   Lookups:
       SourceSystem + SourceJobID
           -> dwh.FactJobPosting.JobPostingKey

       CapabilityName
           -> dwh.DimCapability.CapabilityKey

   Target:
       dwh.BridgeJobPostingCapability

   Grain:
       One row per:
           JobPostingKey + CapabilityKey

   Behaviour:
       - Insert missing relationships
       - Update Confidence when changed
       - Remove stale relationships
       - Idempotent / rerunnable
   ============================================================ */


SET NOCOUNT ON;
SET XACT_ABORT ON;


/* ============================================================
   1. VALIDATE JOB POSTING LOOKUPS
   ============================================================ */

IF EXISTS
(
    SELECT 1

    FROM stg.JobPostingCapability s

    LEFT JOIN dwh.FactJobPosting f
        ON  f.SourceSystem = s.SourceSystem
        AND f.SourceJobID  = s.SourceJobID

    WHERE f.JobPostingKey IS NULL
)
BEGIN

    SELECT
         s.SourceSystem
        ,s.SourceJobID
        ,s.CapabilityName

    FROM stg.JobPostingCapability s

    LEFT JOIN dwh.FactJobPosting f
        ON  f.SourceSystem = s.SourceSystem
        AND f.SourceJobID  = s.SourceJobID

    WHERE f.JobPostingKey IS NULL;

    THROW 50001,
        'Capability bridge load failed: JobPostingKey lookup missing.',
        1;

END;


/* ============================================================
   2. VALIDATE CAPABILITY LOOKUPS
   ============================================================ */

IF EXISTS
(
    SELECT 1

    FROM stg.JobPostingCapability s

    LEFT JOIN dwh.DimCapability c
        ON c.CapabilityName =
           s.CapabilityName

    WHERE c.CapabilityKey IS NULL
)
BEGIN

    SELECT DISTINCT
         s.CapabilityName
        ,s.CapabilityCategory

    FROM stg.JobPostingCapability s

    LEFT JOIN dwh.DimCapability c
        ON c.CapabilityName =
           s.CapabilityName

    WHERE c.CapabilityKey IS NULL;

    THROW 50002,
        'Capability bridge load failed: CapabilityKey lookup missing.',
        1;

END;


/* ============================================================
   3. BUILD CURRENT SOURCE RELATIONSHIPS
   ============================================================ */

IF OBJECT_ID(
    'tempdb..#CapabilityRelationships'
) IS NOT NULL
BEGIN

    DROP TABLE #CapabilityRelationships;

END;


SELECT DISTINCT
     f.JobPostingKey
    ,c.CapabilityKey
    ,s.Confidence

INTO #CapabilityRelationships

FROM stg.JobPostingCapability s

INNER JOIN dwh.FactJobPosting f
    ON  f.SourceSystem = s.SourceSystem
    AND f.SourceJobID  = s.SourceJobID

INNER JOIN dwh.DimCapability c
    ON c.CapabilityName =
       s.CapabilityName;


/* ============================================================
   4. VALIDATE RESOLVED RELATIONSHIPS
   ============================================================ */

DECLARE @StagingRows INT;
DECLARE @ResolvedRows INT;

SELECT
    @StagingRows = COUNT(*)
FROM stg.JobPostingCapability;


SELECT
    @ResolvedRows = COUNT(*)
FROM #CapabilityRelationships;


IF @StagingRows <> @ResolvedRows
BEGIN

    THROW 50003,
        'Capability bridge load failed: staging/resolved row counts differ.',
        1;

END;


/* ============================================================
   5. UPDATE CHANGED CONFIDENCE
   ============================================================ */

UPDATE target

SET
    target.Confidence =
        source.Confidence

FROM dwh.BridgeJobPostingCapability target

INNER JOIN #CapabilityRelationships source
    ON  source.JobPostingKey =
        target.JobPostingKey

    AND source.CapabilityKey =
        target.CapabilityKey

WHERE
    ISNULL(target.Confidence, '') <>
    ISNULL(source.Confidence, '');


DECLARE @UpdatedRows INT = @@ROWCOUNT;


/* ============================================================
   6. INSERT NEW RELATIONSHIPS
   ============================================================ */

INSERT INTO dwh.BridgeJobPostingCapability
(
     JobPostingKey
    ,CapabilityKey
    ,Confidence
)

SELECT
     source.JobPostingKey
    ,source.CapabilityKey
    ,source.Confidence

FROM #CapabilityRelationships source

WHERE NOT EXISTS
(
    SELECT 1

    FROM dwh.BridgeJobPostingCapability target

    WHERE target.JobPostingKey =
          source.JobPostingKey

      AND target.CapabilityKey =
          source.CapabilityKey
);


DECLARE @InsertedRows INT = @@ROWCOUNT;


/* ============================================================
   7. DELETE STALE RELATIONSHIPS
   ============================================================

   stg.JobPostingCapability is a full-refresh representation
   of the current Capability Taxonomy V1.2 result.

   Therefore relationships no longer present in staging
   must also be removed from the DWH bridge.
   ============================================================ */

DELETE target

FROM dwh.BridgeJobPostingCapability target

WHERE NOT EXISTS
(
    SELECT 1

    FROM #CapabilityRelationships source

    WHERE source.JobPostingKey =
          target.JobPostingKey

      AND source.CapabilityKey =
          target.CapabilityKey
);


DECLARE @DeletedRows INT = @@ROWCOUNT;


/* ============================================================
   8. FINAL COUNTS
   ============================================================ */

DECLARE @BridgeRows INT;

SELECT
    @BridgeRows = COUNT(*)
FROM dwh.BridgeJobPostingCapability;


/* ============================================================
   9. LOAD SUMMARY
   ============================================================ */

PRINT '============================================================';
PRINT 'JOB POSTING CAPABILITY BRIDGE LOAD COMPLETED';
PRINT '============================================================';

PRINT
    'Staging rows : '
    + CAST(@StagingRows AS VARCHAR(20));

PRINT
    'Resolved rows: '
    + CAST(@ResolvedRows AS VARCHAR(20));

PRINT
    'Updated rows : '
    + CAST(@UpdatedRows AS VARCHAR(20));

PRINT
    'Inserted rows: '
    + CAST(@InsertedRows AS VARCHAR(20));

PRINT
    'Deleted rows : '
    + CAST(@DeletedRows AS VARCHAR(20));

PRINT
    'Bridge rows  : '
    + CAST(@BridgeRows AS VARCHAR(20));

PRINT '============================================================';


/* ============================================================
   10. CLEANUP
   ============================================================ */

DROP TABLE #CapabilityRelationships;