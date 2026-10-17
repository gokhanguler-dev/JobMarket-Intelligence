IF NOT EXISTS
(
    SELECT 1
    FROM sys.schemas
    WHERE name = 'dwh'
)
BEGIN
    EXEC('CREATE SCHEMA dwh');
END;
GO