/* ============================================================
   15_load_dim_capability.sql

   Purpose:
       Synchronize Capability Taxonomy master data from
       stg.Capability into dwh.DimCapability.

   Source of Truth:
       config/capability_taxonomy.json
            ↓
       stg.Capability
            ↓
       dwh.DimCapability

   Behaviour:
       - Insert new capabilities
       - Update category changes
       - Do not delete historical dimension members
       - Idempotent / rerunnable
   ============================================================ */


SET NOCOUNT ON;
SET XACT_ABORT ON;


/* ============================================================
   1. UPDATE EXISTING CAPABILITIES
   ============================================================ */

UPDATE target
SET
    target.CapabilityCategory =
        source.CapabilityCategory

FROM dwh.DimCapability target

INNER JOIN stg.Capability source
    ON source.CapabilityName =
       target.CapabilityName

WHERE
    ISNULL(target.CapabilityCategory, '') <>
    ISNULL(source.CapabilityCategory, '');


DECLARE @UpdatedRows INT = @@ROWCOUNT;


/* ============================================================
   2. INSERT NEW CAPABILITIES
   ============================================================ */

INSERT INTO dwh.DimCapability
(
     CapabilityName
    ,CapabilityCategory
)
SELECT
     source.CapabilityName
    ,source.CapabilityCategory

FROM stg.Capability source

WHERE NOT EXISTS
(
    SELECT 1

    FROM dwh.DimCapability target

    WHERE target.CapabilityName =
          source.CapabilityName
);


DECLARE @InsertedRows INT = @@ROWCOUNT;


/* ============================================================
   3. LOAD SUMMARY
   ============================================================ */

DECLARE @DimensionRows INT;

SELECT
    @DimensionRows = COUNT(*)
FROM dwh.DimCapability;


PRINT '============================================================';
PRINT 'DIM CAPABILITY LOAD COMPLETED';
PRINT '============================================================';

PRINT
    'Updated rows : '
    + CAST(@UpdatedRows AS VARCHAR(20));

PRINT
    'Inserted rows: '
    + CAST(@InsertedRows AS VARCHAR(20));

PRINT
    'Total rows   : '
    + CAST(@DimensionRows AS VARCHAR(20));

PRINT '============================================================';