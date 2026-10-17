IF OBJECT_ID('dwh.DimLocation', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimLocation
    (
        LocationKey     INT IDENTITY(1,1) NOT NULL,
        LocationName    NVARCHAR(500) NOT NULL,
        CreatedAt       DATETIME2(0) NOT NULL
                        CONSTRAINT DF_DimLocation_CreatedAt
                        DEFAULT SYSDATETIME(),

        CONSTRAINT PK_DimLocation
            PRIMARY KEY (LocationKey),

        CONSTRAINT UQ_DimLocation_LocationName
            UNIQUE (LocationName)
    );
END;
GO