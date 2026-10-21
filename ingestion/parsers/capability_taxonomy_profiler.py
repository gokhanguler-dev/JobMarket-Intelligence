import re
from collections import Counter, defaultdict

from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.job_text_parser import clean_html_text


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

CAPABILITY_VERBS = {
    "build",
    "develop",
    "design",
    "implement",
    "maintain",
    "manage",
    "monitor",
    "optimize",
    "automate",
    "deploy",
    "integrate",
    "architect",
    "configure",
    "administer",
    "troubleshoot",
    "test",
    "secure",
    "analyze",
    "model",
    "process",
    "transform",
    "orchestrate",
    "migrate",
    "scale",
    "operate",
    "support",
    "debug",
    "review",
    "document",
    "deliver",
}

GENERIC_OBJECTS = {
    "team",
    "teams",
    "company",
    "business",
    "organization",
    "organisation",
    "customer",
    "customers",
    "client",
    "clients",
    "product",
    "products",
    "solution",
    "solutions",
    "project",
    "projects",
}


# ------------------------------------------------------------
# DATA
# ------------------------------------------------------------

def get_tech_jobs():
    query = """
    SELECT
         f.JobPostingKey
        ,f.SourceSystem
        ,f.SourceJobID
        ,f.JobTitle
        ,ca.CareerAreaName
        ,r.RoleName
        ,f.Seniority
        ,latest.Description
    FROM dwh.FactJobPosting f

    LEFT JOIN dwh.DimCareerArea ca
        ON ca.CareerAreaKey = f.CareerAreaKey

    LEFT JOIN dwh.DimRole r
        ON r.RoleKey = f.RoleKey

    OUTER APPLY
    (
        SELECT TOP 1
            jp.Description
        FROM stg.JobPosting jp
        WHERE jp.SourceSystem = f.SourceSystem
          AND jp.SourceJobID = f.SourceJobID
        ORDER BY
             jp.ExtractedAt DESC
            ,jp.JobPostingStgID DESC
    ) latest

    WHERE f.IsTechRole = 'Tech'
    ORDER BY f.JobPostingKey;
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        columns = [column[0] for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


# ------------------------------------------------------------
# TEXT
# ------------------------------------------------------------

def normalize_text(text):
    if not text:
        return ""

    text = clean_html_text(text)

    text = (
        text.replace("•", ". ")
        .replace("●", ". ")
        .replace("▪", ". ")
        .replace("–", ". ")
        .replace("—", ". ")
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_segments(text):
    """
    Description'ı kısa sentence/bullet benzeri parçalara ayırır.
    """
    return [
        segment.strip()
        for segment in re.split(r"[.!?;\n]+", text)
        if segment.strip()
    ]


# ------------------------------------------------------------
# CAPABILITY CANDIDATES
# ------------------------------------------------------------

def extract_action_phrases(segment):
    """
    Verb'den başlayıp sonraki birkaç kelimeyi alır.

    Example:
        design scalable data pipelines
        optimize database performance
        implement ci/cd pipelines
    """

    words = re.findall(
        r"[A-Za-z0-9+#./-]+",
        segment.lower()
    )

    results = []

    for index, word in enumerate(words):

        if word not in CAPABILITY_VERBS:
            continue

        # verb + maksimum 6 kelime
        phrase_words = words[index:index + 7]

        if len(phrase_words) < 2:
            continue

        # Son derece generic verb-object kombinasyonlarını azalt.
        if (
            len(phrase_words) >= 2
            and phrase_words[1] in GENERIC_OBJECTS
        ):
            continue

        phrase = " ".join(phrase_words)

        results.append(phrase)

    return results


def profile_capabilities(jobs):
    phrase_jobs = defaultdict(set)
    phrase_areas = defaultdict(set)
    phrase_roles = defaultdict(set)
    examples = defaultdict(list)

    for job in jobs:

        text = normalize_text(job.get("Description"))

        if not text:
            continue

        segments = split_segments(text)

        seen_in_job = set()

        for segment in segments:

            phrases = extract_action_phrases(segment)

            for phrase in phrases:

                if phrase in seen_in_job:
                    continue

                seen_in_job.add(phrase)

                phrase_jobs[phrase].add(
                    job["JobPostingKey"]
                )

                if job.get("CareerAreaName"):
                    phrase_areas[phrase].add(
                        job["CareerAreaName"]
                    )

                if job.get("RoleName"):
                    phrase_roles[phrase].add(
                        job["RoleName"]
                    )

                if len(examples[phrase]) < 2:
                    examples[phrase].append(
                        (
                            job.get("JobTitle"),
                            segment[:180]
                        )
                    )

    return (
        phrase_jobs,
        phrase_areas,
        phrase_roles,
        examples
    )


# ------------------------------------------------------------
# VERB PROFILE
# ------------------------------------------------------------

def profile_verbs(jobs):
    counter = Counter()

    for job in jobs:

        text = normalize_text(job.get("Description"))

        if not text:
            continue

        words = set(
            re.findall(
                r"[A-Za-z]+",
                text.lower()
            )
        )

        for verb in CAPABILITY_VERBS:

            if verb in words:
                counter[verb] += 1

    return counter


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

def main():

    jobs = get_tech_jobs()

    (
        phrase_jobs,
        phrase_areas,
        phrase_roles,
        examples
    ) = profile_capabilities(jobs)

    verb_counter = profile_verbs(jobs)

    print()
    print("=" * 100)
    print("CAPABILITY PROFILER V2")
    print("=" * 100)

    print(f"Tech jobs : {len(jobs)}")

    print()
    print("=" * 100)
    print("ACTION VERB COVERAGE")
    print("=" * 100)

    for verb, count in verb_counter.most_common():
        print(
            f"{verb:20}"
            f"{count:>8}"
        )

    print()
    print("=" * 100)
    print("CAPABILITY CANDIDATE PHRASES")
    print("=" * 100)

    rows = []

    for phrase, job_keys in phrase_jobs.items():

        job_count = len(job_keys)

        if job_count < 2:
            continue

        rows.append(
            (
                phrase,
                job_count,
                len(phrase_areas[phrase]),
                len(phrase_roles[phrase])
            )
        )

    rows.sort(
        key=lambda x: (-x[1], x[0])
    )

    for (
        phrase,
        job_count,
        area_count,
        role_count
    ) in rows[:100]:

        print()
        print(
            f"[{job_count:>2} jobs | "
            f"{area_count} areas | "
            f"{role_count} roles] "
            f"{phrase}"
        )

        for title, example in examples[phrase]:
            print(
                f"    - {title}: {example}"
            )


if __name__ == "__main__":
    main()