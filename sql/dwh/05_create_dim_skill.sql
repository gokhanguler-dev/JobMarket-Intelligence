IF OBJECT_ID('dwh.DimSkill', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimSkill
    (
        SkillKey        INT IDENTITY(1,1) NOT NULL,
        SkillName       NVARCHAR(200) NOT NULL,
        CreatedAt       DATETIME2(0) NOT NULL
                        CONSTRAINT DF_DimSkill_CreatedAt
                        DEFAULT SYSDATETIME(),

        CONSTRAINT PK_DimSkill
            PRIMARY KEY (SkillKey),

        CONSTRAINT UQ_DimSkill_SkillName
            UNIQUE (SkillName)
    );
END;
GO