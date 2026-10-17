IF OBJECT_ID('dwh.DimRole', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimRole
    (
        RoleKey         INT IDENTITY(1,1) NOT NULL,
        RoleName        NVARCHAR(200) NOT NULL,
        CreatedAt       DATETIME2(0) NOT NULL
                        CONSTRAINT DF_DimRole_CreatedAt
                        DEFAULT SYSDATETIME(),

        CONSTRAINT PK_DimRole
            PRIMARY KEY (RoleKey),

        CONSTRAINT UQ_DimRole_RoleName
            UNIQUE (RoleName)
    );
END;
GO