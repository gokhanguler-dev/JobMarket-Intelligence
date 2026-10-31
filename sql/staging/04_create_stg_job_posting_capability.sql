USE JobMarketDWH;
GO

/* ============================================================
   STG - JOB POSTING CAPABILITY

   Grain:
   1 row = 1 Job Posting + 1 Capability relationship

   Natural Key:
   SourceSystem + SourceJobID + CapabilityName

   Populated by:
   capability_staging_loader.py
   ============================================================ */

IF OBJECT_ID('stg.JobPostingCapability', 'U') IS NULL
BEGIN

    CREATE TABLE stg.JobPostingCapability
    (
         SourceSystem        VARCHAR(50)   NOT NULL
        ,SourceJobID         BIGINT        NOT NULL
        ,CapabilityName      NVARCHAR(200) NOT NULL
        ,CapabilityCategory  NVARCHAR(200) NOT NULL
        ,Confidence          VARCHAR(50)   NOT NULL

        CONSTRAINT PK_stg_JobPostingCapability
            PRIMARY KEY
            (
                 SourceSystem
                ,SourceJobID
                ,CapabilityName
            )
    );

END;
GO