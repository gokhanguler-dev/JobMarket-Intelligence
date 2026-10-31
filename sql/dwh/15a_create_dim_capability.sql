USE JobMarketDWH;
GO

/* ============================================================
   DWH - DIM CAPABILITY

   Grain:
   1 row = 1 unique capability

   Source:
   stg.Capability
   ============================================================ */

IF OBJECT_ID('dwh.DimCapability', 'U') IS NULL
BEGIN

    CREATE TABLE dwh.DimCapability
    (
         CapabilityKey       INT IDENTITY(1,1) NOT NULL
        ,CapabilityName      NVARCHAR(200) NOT NULL
        ,CapabilityCategory  NVARCHAR(200) NOT NULL

        CONSTRAINT PK_DimCapability
            PRIMARY KEY (CapabilityKey),

        CONSTRAINT UQ_DimCapability_CapabilityName
            UNIQUE (CapabilityName)
    );

END;
GO