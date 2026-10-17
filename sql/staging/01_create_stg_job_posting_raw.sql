USE JobMarketDWH;
GO

/* ============================================================
   JobMarket Intelligence

   Layer  : STG
   Table  : stg.JobPostingRaw
   Purpose:
       Stores job postings collected from external job sources
       in a source-aligned structure before normalization.

   Source:
       Jooble API

   Notes:
       - No business normalization is applied in this layer.
       - Search parameters are stored for lineage.
       - SourceJobID + Source identify the source record.
   ============================================================ */


---------------------------------------------------------------
-- CREATE STG SCHEMA
---------------------------------------------------------------

IF NOT EXISTS
(
    SELECT 1
    FROM sys.schemas
    WHERE name = 'stg'
)
BEGIN
    EXEC('CREATE SCHEMA stg');
END;
GO


---------------------------------------------------------------
-- CREATE RAW JOB POSTING TABLE
---------------------------------------------------------------

IF OBJECT_ID('stg.JobPostingRaw', 'U') IS NULL
BEGIN

    CREATE TABLE stg.JobPostingRaw
    (
        RawJobPostingID BIGINT IDENTITY(1,1) NOT NULL,

        -- Source identification
        SourceJobID     BIGINT          NOT NULL,
        SourceSystem    VARCHAR(50)     NOT NULL,

        -- Search lineage
        SearchKeyword   NVARCHAR(200)   NULL,
        SearchLocation  NVARCHAR(200)   NULL,

        -- Source attributes
        JobTitle        NVARCHAR(500)   NULL,
        JobLocation     NVARCHAR(500)   NULL,
        Snippet         NVARCHAR(MAX)   NULL,
        Salary          NVARCHAR(500)   NULL,
        Source          NVARCHAR(500)   NULL,
        EmploymentType  NVARCHAR(200)   NULL,
        JobLink         NVARCHAR(2000)  NULL,
        Company         NVARCHAR(500)   NULL,

        SourceUpdatedAt DATETIMEOFFSET  NULL,

        -- Ingestion metadata
        IngestedAt      DATETIME2(0)    NOT NULL
            CONSTRAINT DF_JobPostingRaw_IngestedAt
            DEFAULT SYSDATETIME(),

        RawFileName     NVARCHAR(500)   NULL,

        CONSTRAINT PK_JobPostingRaw
            PRIMARY KEY (RawJobPostingID)
    );

END;
GO