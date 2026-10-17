IF OBJECT_ID('dwh.BridgeJobPostingSkill', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.BridgeJobPostingSkill
    (
        JobPostingKey    BIGINT NOT NULL,
        SkillKey         INT NOT NULL,

        CreatedAt        DATETIME2(0) NOT NULL
                         CONSTRAINT DF_BridgeJobPostingSkill_CreatedAt
                         DEFAULT SYSDATETIME(),

        CONSTRAINT PK_BridgeJobPostingSkill
            PRIMARY KEY
            (
                JobPostingKey,
                SkillKey
            ),

        CONSTRAINT FK_BridgeJobPostingSkill_JobPosting
            FOREIGN KEY (JobPostingKey)
            REFERENCES dwh.FactJobPosting(JobPostingKey),

        CONSTRAINT FK_BridgeJobPostingSkill_Skill
            FOREIGN KEY (SkillKey)
            REFERENCES dwh.DimSkill(SkillKey)
    );
END;
GO