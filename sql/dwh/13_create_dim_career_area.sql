USE JobMarketDWH;
GO

/* ============================================================
   13_create_dim_career_area.sql

   Purpose:
       Creates the Career Area dimension used by the
       Job Classification V4.2 pipeline.

   Notes:
       - Idempotent
       - Career areas are controlled taxonomy values.
       - Unknown / Out of Scope / Other Tech are explicit
         semantic members instead of NULL values.
   ============================================================ */


------------------------------------------------------------
-- 1. CREATE DIMENSION
------------------------------------------------------------

IF OBJECT_ID('dwh.DimCareerArea', 'U') IS NULL
BEGIN

    CREATE TABLE dwh.DimCareerArea
    (
         CareerAreaKey   INT IDENTITY(1,1) NOT NULL
        ,CareerAreaName  NVARCHAR(200) NOT NULL
        ,IsActive        BIT NOT NULL
            CONSTRAINT DF_DimCareerArea_IsActive
            DEFAULT (1)

        ,CreatedAt       DATETIME2(0) NOT NULL
            CONSTRAINT DF_DimCareerArea_CreatedAt
            DEFAULT (SYSDATETIME())

        ,CONSTRAINT PK_DimCareerArea
            PRIMARY KEY CLUSTERED (CareerAreaKey)

        ,CONSTRAINT UQ_DimCareerArea_CareerAreaName
            UNIQUE (CareerAreaName)
    );

END;
GO


------------------------------------------------------------
-- 2. SEED CAREER AREAS
------------------------------------------------------------

DECLARE @CareerAreas TABLE
(
    CareerAreaName NVARCHAR(200) NOT NULL
);

INSERT INTO @CareerAreas
(
    CareerAreaName
)
VALUES
     (N'Data & Analytics')
    ,(N'AI & Machine Learning')
    ,(N'Software Engineering')
    ,(N'Cloud, DevOps & Platform')
    ,(N'Cybersecurity')
    ,(N'Enterprise Applications')
    ,(N'IT Operations & Support')
    ,(N'Other Tech')
    ,(N'Out of Scope')
    ,(N'Unknown');


INSERT INTO dwh.DimCareerArea
(
     CareerAreaName
    ,IsActive
)
SELECT
     s.CareerAreaName
    ,1
FROM @CareerAreas s
WHERE NOT EXISTS
(
    SELECT 1
    FROM dwh.DimCareerArea d
    WHERE d.CareerAreaName = s.CareerAreaName
);
GO


------------------------------------------------------------
-- 3. VALIDATION
------------------------------------------------------------

SELECT
     CareerAreaKey
    ,CareerAreaName
    ,IsActive
    ,CreatedAt
FROM dwh.DimCareerArea
ORDER BY CareerAreaKey;
GO