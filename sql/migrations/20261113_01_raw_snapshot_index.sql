IF DB_NAME() <> N'JobMarketDWH'
    THROW 51000, 'Select JobMarketDWH before applying this migration.', 1;

DECLARE @keyBytes int;
SELECT @keyBytes = SUM(CONVERT(int, max_length))
FROM sys.columns
WHERE object_id = OBJECT_ID(N'stg.JobPostingRaw')
  AND name IN (N'SourceSystem', N'SourceJobID', N'RawFileName')
HAVING COUNT(*) = 3 AND MIN(max_length) > 0;

IF @keyBytes IS NULL OR @keyBytes > 1700
    THROW 51000, 'RAW lookup columns are missing or exceed the nonclustered key limit.', 1;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'stg.JobPostingRaw')
      AND name = N'IX_JobPostingRaw_SnapshotLookup'
)
    CREATE NONCLUSTERED INDEX IX_JobPostingRaw_SnapshotLookup
        ON stg.JobPostingRaw (SourceSystem, SourceJobID, RawFileName);
