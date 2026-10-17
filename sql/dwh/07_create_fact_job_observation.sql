IF OBJECT_ID('dwh.FactJobObservation', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.FactJobObservation
    (
        JobObservationKey    BIGINT IDENTITY(1,1) NOT NULL,

        JobPostingKey        BIGINT NOT NULL,
        RawJobPostingID      BIGINT NOT NULL,

        SearchKeyword        NVARCHAR(200) NULL,
        SearchLocation       NVARCHAR(200) NULL,
        RawFileName          NVARCHAR(500) NULL,

        ObservedAt           DATETIME2(0) NOT NULL,

        CreatedAt            DATETIME2(0) NOT NULL
                             CONSTRAINT DF_FactJobObservation_CreatedAt
                             DEFAULT SYSDATETIME(),

        CONSTRAINT PK_FactJobObservation
            PRIMARY KEY (JobObservationKey),

        CONSTRAINT UQ_FactJobObservation_RawJobPostingID
            UNIQUE (RawJobPostingID),

        CONSTRAINT FK_FactJobObservation_JobPosting
            FOREIGN KEY (JobPostingKey)
            REFERENCES dwh.FactJobPosting(JobPostingKey)
    );
END;
GO