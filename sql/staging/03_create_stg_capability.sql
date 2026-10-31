USE JobMarketDWH;
GO

/* ============================================================
   STG - CAPABILITY TAXONOMY

   Grain:
   1 row = 1 unique capability

   Source:
   config/capability_taxonomy.json
   ============================================================ */

IF OBJECT_ID('stg.Capability', 'U') IS NULL
BEGIN
    CREATE TABLE stg.Capability
    (
        CapabilityName      NVARCHAR(200) NOT NULL,
        CapabilityCategory  NVARCHAR(200) NOT NULL,

        CONSTRAINT PK_stg_Capability
            PRIMARY KEY (CapabilityName)
    );
END;
GO