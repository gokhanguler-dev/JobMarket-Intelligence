USE JobMarketDWH;
GO

/* ============================================================
   DWH - BRIDGE JOB POSTING CAPABILITY

   Grain:
   1 row = 1 Job Posting + 1 Capability relationship

   Foreign Keys:
   JobPostingKey -> dwh.FactJobPosting
   CapabilityKey -> dwh.DimCapability
   ============================================================ */

IF OBJECT_ID('dwh.BridgeJobPostingCapability', 'U') IS NULL
BEGIN

    CREATE TABLE dwh.BridgeJobPostingCapability
    (
         JobPostingKey  BIGINT      NOT NULL
        ,CapabilityKey  INT         NOT NULL
        ,Confidence     VARCHAR(50) NOT NULL

        CONSTRAINT PK_BridgeJobPostingCapability
            PRIMARY KEY
            (
                 JobPostingKey
                ,CapabilityKey
            ),

        CONSTRAINT FK_BridgeJobPostingCapability_JobPosting
            FOREIGN KEY (JobPostingKey)
            REFERENCES dwh.FactJobPosting(JobPostingKey),

        CONSTRAINT FK_BridgeJobPostingCapability_Capability
            FOREIGN KEY (CapabilityKey)
            REFERENCES dwh.DimCapability(CapabilityKey)
    );

END;
GO