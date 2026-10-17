USE JobMarketDWH;
GO


/* ============================================================
   STG - CLEANED JOB POSTING

   Raw source data is transformed into a cleaned,
   analysis-ready staging structure.

   One row represents one RAW job posting snapshot.
   ============================================================ */


IF OBJECT_ID('stg.JobPosting', 'U') IS NULL
BEGIN

    CREATE TABLE stg.JobPosting
    (
        JobPostingStgID BIGINT IDENTITY(1,1) NOT NULL,

        RawJobPostingID BIGINT NOT NULL,

        SourceJobID     BIGINT NOT NULL,
        SourceSystem    VARCHAR(50) NOT NULL,

        SearchKeyword   NVARCHAR(200) NULL,
        SearchLocation  NVARCHAR(200) NULL,

        JobTitle        NVARCHAR(500) NULL,
        Company         NVARCHAR(500) NULL,
        JobLocation     NVARCHAR(500) NULL,

        CleanSnippet    NVARCHAR(MAX) NULL,

        Salary          NVARCHAR(500) NULL,
        EmploymentType  NVARCHAR(200) NULL,

        JobLink         NVARCHAR(2000) NULL,

        SourceUpdatedAt DATETIMEOFFSET NULL,

        ProcessedAt     DATETIME2(0) NOT NULL
            CONSTRAINT DF_JobPosting_ProcessedAt
            DEFAULT SYSDATETIME(),

        CONSTRAINT PK_JobPosting
            PRIMARY KEY (JobPostingStgID),

        CONSTRAINT FK_JobPosting_JobPostingRaw
            FOREIGN KEY (RawJobPostingID)
            REFERENCES stg.JobPostingRaw(RawJobPostingID),

        CONSTRAINT UQ_JobPosting_RawJobPostingID
            UNIQUE (RawJobPostingID)
    );

END;
GO

USE JobMarketDWH;
GO


/* ============================================================
   STG - CLEANED JOB POSTING

   Raw source data is transformed into a cleaned,
   analysis-ready staging structure.

   One row represents one RAW job posting snapshot.
   ============================================================ */
   /* ============================================================
   STG - JOB POSTING SKILLS

   Stores skills detected from job title + cleaned snippet.

   One job posting can contain multiple skills.
   ============================================================ */


IF OBJECT_ID('stg.JobPostingSkill', 'U') IS NULL
BEGIN

    CREATE TABLE stg.JobPostingSkill
    (
        JobPostingSkillID BIGINT IDENTITY(1,1) NOT NULL,

        JobPostingStgID   BIGINT NOT NULL,

        SkillName         NVARCHAR(200) NOT NULL,

        DetectedAt        DATETIME2(0) NOT NULL
            CONSTRAINT DF_JobPostingSkill_DetectedAt
            DEFAULT SYSDATETIME(),

        CONSTRAINT PK_JobPostingSkill
            PRIMARY KEY (JobPostingSkillID),

        CONSTRAINT FK_JobPostingSkill_JobPosting
            FOREIGN KEY (JobPostingStgID)
            REFERENCES stg.JobPosting(JobPostingStgID),

        CONSTRAINT UQ_JobPostingSkill
            UNIQUE
            (
                JobPostingStgID,
                SkillName
            )
    );

END;
GO