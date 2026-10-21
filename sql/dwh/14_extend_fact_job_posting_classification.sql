USE JobMarketDWH;
GO

/* ============================================================
   14_extend_fact_job_posting_classification.sql

   Purpose:
       Extends FactJobPosting with classification attributes
       produced by Job Classification V4.2.

   Classification fields:
       IsTechRole
       CareerAreaKey
       ClassificationConfidence
       ClassificationVersion

   Notes:
       Existing records remain NULL until classifier backfill.
   ============================================================ */


------------------------------------------------------------
-- 1. IsTechRole
------------------------------------------------------------

IF COL_LENGTH(
    'dwh.FactJobPosting',
    'IsTechRole'
) IS NULL
BEGIN

    ALTER TABLE dwh.FactJobPosting
    ADD IsTechRole NVARCHAR(20) NULL;

END;
GO


------------------------------------------------------------
-- 2. CareerAreaKey
------------------------------------------------------------

IF COL_LENGTH(
    'dwh.FactJobPosting',
    'CareerAreaKey'
) IS NULL
BEGIN

    ALTER TABLE dwh.FactJobPosting
    ADD CareerAreaKey INT NULL;

END;
GO


------------------------------------------------------------
-- 3. ClassificationConfidence
------------------------------------------------------------

IF COL_LENGTH(
    'dwh.FactJobPosting',
    'ClassificationConfidence'
) IS NULL
BEGIN

    ALTER TABLE dwh.FactJobPosting
    ADD ClassificationConfidence NVARCHAR(20) NULL;

END;
GO


------------------------------------------------------------
-- 4. ClassificationVersion
------------------------------------------------------------

IF COL_LENGTH(
    'dwh.FactJobPosting',
    'ClassificationVersion'
) IS NULL
BEGIN

    ALTER TABLE dwh.FactJobPosting
    ADD ClassificationVersion VARCHAR(20) NULL;

END;
GO


------------------------------------------------------------
-- 5. FOREIGN KEY
------------------------------------------------------------

IF NOT EXISTS
(
    SELECT 1
    FROM sys.foreign_keys
    WHERE name =
        'FK_FactJobPosting_CareerArea'
)
BEGIN

    ALTER TABLE dwh.FactJobPosting
    ADD CONSTRAINT FK_FactJobPosting_CareerArea
        FOREIGN KEY (CareerAreaKey)
        REFERENCES dwh.DimCareerArea
        (
            CareerAreaKey
        );

END;
GO


------------------------------------------------------------
-- 6. VALIDATION - NEW COLUMNS
------------------------------------------------------------

SELECT
     c.column_id
    ,c.name AS ColumnName
    ,t.name AS DataType
    ,c.max_length AS MaxLength
    ,c.is_nullable AS IsNullable
FROM sys.columns c
INNER JOIN sys.types t
    ON c.user_type_id = t.user_type_id
WHERE c.object_id =
    OBJECT_ID('dwh.FactJobPosting')
ORDER BY c.column_id;
GO


------------------------------------------------------------
-- 7. VALIDATION - FOREIGN KEY
------------------------------------------------------------

SELECT
     fk.name AS ForeignKeyName
    ,OBJECT_NAME(
        fkc.parent_object_id
     ) AS ParentTable
    ,pc.name AS ParentColumn
    ,OBJECT_NAME(
        fkc.referenced_object_id
     ) AS ReferencedTable
    ,rc.name AS ReferencedColumn
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc
    ON fk.object_id =
       fkc.constraint_object_id
INNER JOIN sys.columns pc
    ON pc.object_id =
       fkc.parent_object_id
   AND pc.column_id =
       fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id =
       fkc.referenced_object_id
   AND rc.column_id =
       fkc.referenced_column_id
WHERE fkc.parent_object_id =
    OBJECT_ID('dwh.FactJobPosting')
ORDER BY fk.name;
GO