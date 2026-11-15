IF DB_NAME() <> N'JobMarketDWH'
    THROW 51000, 'Select JobMarketDWH before applying this migration.', 1;

IF OBJECT_ID(N'stg.RawFileCheckpoint', N'U') IS NULL
    CREATE TABLE stg.RawFileCheckpoint (
        CheckpointID bigint IDENTITY NOT NULL PRIMARY KEY CLUSTERED,
        SourceSystem varchar(50) NOT NULL,
        RawFileName nvarchar(500) NOT NULL,
        ContentSHA256 binary(32) NOT NULL,
        CompletedAtUTC datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_RawFileCheckpoint UNIQUE NONCLUSTERED (SourceSystem, RawFileName)
    );
