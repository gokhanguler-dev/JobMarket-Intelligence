IF OBJECT_ID('dwh.FactJobPosting', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.FactJobPosting
    (
        JobPostingKey      BIGINT IDENTITY(1,1) NOT NULL,

        SourceJobID        BIGINT NOT NULL,
        SourceSystem       VARCHAR(50) NOT NULL,

        CompanyKey         INT NULL,
        LocationKey        INT NULL,
        RoleKey            INT NULL,

        JobTitle           NVARCHAR(500) NULL,
        Seniority          NVARCHAR(100) NULL,
        EmploymentType     NVARCHAR(200) NULL,
        Salary             NVARCHAR(500) NULL,
        JobLink            NVARCHAR(2000) NULL,

        SourceUpdatedAt    DATETIMEOFFSET NULL,

        FirstObservedAt    DATETIME2(0) NOT NULL,
        LastObservedAt     DATETIME2(0) NOT NULL,

        CreatedAt          DATETIME2(0) NOT NULL
                           CONSTRAINT DF_FactJobPosting_CreatedAt
                           DEFAULT SYSDATETIME(),

        CONSTRAINT PK_FactJobPosting
            PRIMARY KEY (JobPostingKey),

        CONSTRAINT UQ_FactJobPosting_Source
            UNIQUE (SourceSystem, SourceJobID),

        CONSTRAINT FK_FactJobPosting_Company
            FOREIGN KEY (CompanyKey)
            REFERENCES dwh.DimCompany(CompanyKey),

        CONSTRAINT FK_FactJobPosting_Location
            FOREIGN KEY (LocationKey)
            REFERENCES dwh.DimLocation(LocationKey),

        CONSTRAINT FK_FactJobPosting_Role
            FOREIGN KEY (RoleKey)
            REFERENCES dwh.DimRole(RoleKey)
    );
END;
GO