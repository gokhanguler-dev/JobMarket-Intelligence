USE JobMarketDWH;
GO

/* ============================================================
   FACT JOB OBSERVATION

   Grain:
   1 row = 1 RAW observation

   Aynı JobPosting birden fazla:
   - SearchKeyword
   - snapshot
   - collection run

   üzerinden gözlemlenebilir.
   ============================================================ */

INSERT INTO dwh.FactJobObservation
(
    JobPostingKey,
    RawJobPostingID,
    SearchKeyword,
    SearchLocation,
    RawFileName,
    ObservedAt
)

SELECT
    f.JobPostingKey,
    r.RawJobPostingID,
    r.SearchKeyword,
    r.SearchLocation,
    r.RawFileName,
    r.IngestedAt

FROM stg.JobPostingRaw r

INNER JOIN dwh.FactJobPosting f
    ON  f.SourceSystem = r.SourceSystem
    AND f.SourceJobID = r.SourceJobID

WHERE NOT EXISTS
(
    SELECT 1
    FROM dwh.FactJobObservation o
    WHERE o.RawJobPostingID = r.RawJobPostingID
);
GO