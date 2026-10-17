IF OBJECT_ID('dwh.DimCompany', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimCompany
    (
        CompanyKey      INT IDENTITY(1,1) NOT NULL,
        CompanyName     NVARCHAR(500) NOT NULL,
        CreatedAt       DATETIME2(0) NOT NULL
                        CONSTRAINT DF_DimCompany_CreatedAt
                        DEFAULT SYSDATETIME(),

        CONSTRAINT PK_DimCompany
            PRIMARY KEY (CompanyKey),

        CONSTRAINT UQ_DimCompany_CompanyName
            UNIQUE (CompanyName)
    );
END;
GO