USE JobMarketDWH;
GO

/* ============================================================
   FACT JOB POSTING - INCREMENTAL UPSERT

   Grain:
   1 row = 1 unique SourceSystem + SourceJobID

   Davranış:
   - Yeni ilan          -> INSERT
   - Mevcut ilan        -> UPDATE
   - FirstObservedAt    -> ilk observation
   - LastObservedAt     -> son observation
   - Descriptive fields -> en güncel STG observation
   ============================================================ */

DROP TABLE IF EXISTS #FactJobPostingSource;


/* ============================================================
   1. Observation istatistikleri
   ============================================================ */

;WITH ObservationStats AS
(
    SELECT
        SourceSystem,
        SourceJobID,
        MIN(IngestedAt) AS FirstObservedAt,
        MAX(IngestedAt) AS LastObservedAt
    FROM stg.JobPostingRaw
    GROUP BY
        SourceSystem,
        SourceJobID
),

/* ============================================================
   2. Her unique job için en güncel STG kaydı
   ============================================================ */

LatestJob AS
(
    SELECT
        jp.*,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                jp.SourceSystem,
                jp.SourceJobID

            ORDER BY
                r.IngestedAt DESC,
                jp.RawJobPostingID DESC
        ) AS RowNo

    FROM stg.JobPosting jp

    INNER JOIN stg.JobPostingRaw r
        ON r.RawJobPostingID = jp.RawJobPostingID
)

SELECT
    lj.SourceJobID,
    lj.SourceSystem,

    dc.CompanyKey,
    dl.LocationKey,
    dr.RoleKey,

    lj.JobTitle,
    lj.Seniority,
    lj.EmploymentType,
    lj.Salary,
    lj.JobLink,
    lj.SourceUpdatedAt,

    os.FirstObservedAt,
    os.LastObservedAt

INTO #FactJobPostingSource

FROM LatestJob lj

INNER JOIN ObservationStats os
    ON  os.SourceSystem = lj.SourceSystem
    AND os.SourceJobID   = lj.SourceJobID

LEFT JOIN dwh.DimCompany dc
    ON dc.CompanyName = LTRIM(RTRIM(lj.Company))

LEFT JOIN dwh.DimLocation dl
    ON dl.LocationName = LTRIM(RTRIM(lj.JobLocation))

LEFT JOIN dwh.DimRole dr
    ON dr.RoleName = LTRIM(RTRIM(lj.NormalizedRole))

WHERE lj.RowNo = 1;


/* ============================================================
   3. Mevcut job'ları UPDATE et
   ============================================================ */

UPDATE tgt

SET
    tgt.CompanyKey       = src.CompanyKey,
    tgt.LocationKey      = src.LocationKey,
    tgt.RoleKey          = src.RoleKey,
    tgt.JobTitle         = src.JobTitle,
    tgt.Seniority        = src.Seniority,
    tgt.EmploymentType   = src.EmploymentType,
    tgt.Salary           = src.Salary,
    tgt.JobLink          = src.JobLink,
    tgt.SourceUpdatedAt  = src.SourceUpdatedAt,

    /* İlk görülme tarihi geriye gitmişse koru */
    tgt.FirstObservedAt =
        CASE
            WHEN src.FirstObservedAt < tgt.FirstObservedAt
                THEN src.FirstObservedAt
            ELSE tgt.FirstObservedAt
        END,

    /* Son görülme tarihi ilerlemişse güncelle */
    tgt.LastObservedAt =
        CASE
            WHEN src.LastObservedAt > tgt.LastObservedAt
                THEN src.LastObservedAt
            ELSE tgt.LastObservedAt
        END

FROM dwh.FactJobPosting tgt

INNER JOIN #FactJobPostingSource src
    ON  src.SourceSystem = tgt.SourceSystem
    AND src.SourceJobID   = tgt.SourceJobID;


/* ============================================================
   4. Yeni job'ları INSERT et
   ============================================================ */

INSERT INTO dwh.FactJobPosting
(
    SourceJobID,
    SourceSystem,

    CompanyKey,
    LocationKey,
    RoleKey,

    JobTitle,
    Seniority,
    EmploymentType,
    Salary,
    JobLink,
    SourceUpdatedAt,

    FirstObservedAt,
    LastObservedAt
)

SELECT
    src.SourceJobID,
    src.SourceSystem,

    src.CompanyKey,
    src.LocationKey,
    src.RoleKey,

    src.JobTitle,
    src.Seniority,
    src.EmploymentType,
    src.Salary,
    src.JobLink,
    src.SourceUpdatedAt,

    src.FirstObservedAt,
    src.LastObservedAt

FROM #FactJobPostingSource src

WHERE NOT EXISTS
(
    SELECT 1
    FROM dwh.FactJobPosting tgt

    WHERE tgt.SourceSystem = src.SourceSystem
      AND tgt.SourceJobID   = src.SourceJobID
);


DROP TABLE IF EXISTS #FactJobPostingSource;
GO