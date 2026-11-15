"""Track committed snapshot contents independently of collector manifests."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
import os


CHECKPOINT = "stg.RawFileCheckpoint"


def ingest_files(connection, source, paths, load_file, *, replay=False):
    """Commit each snapshot and its digest together on a dedicated connection."""
    if connection.autocommit:
        raise ValueError("RAW checkpoint ingestion requires transactional SQL Server connections.")
    totals = [0, 0]
    with closing(connection.cursor()) as cursor:
        for path in paths:
            try:
                # A key-range lock also serializes the first load of a filename.
                cursor.execute(f"""
                    SELECT ContentSHA256 FROM {CHECKPOINT} WITH (UPDLOCK, HOLDLOCK)
                    WHERE SourceSystem = CONVERT(varchar(50), ?) AND RawFileName = ?
                """, source, path.name)
                previous = cursor.fetchone()
                payload = path.read_bytes()
                digest = sha256(payload).digest()
                if previous and previous[0] == digest and not replay:
                    connection.commit()
                    totals[1] += 1
                    continue

                snapshot = json.loads(payload.decode("utf-8"))
                if snapshot.get("metadata", {}).get("source_system", source) != source:
                    raise ValueError(f"Snapshot source does not match loader: {path.name}")
                jobs_container = snapshot if source == "Workday" else snapshot.get("response")
                if not isinstance(jobs_container, dict) or not isinstance(jobs_container.get("jobs"), list):
                    raise ValueError(f"Snapshot has no jobs array: {path.name}")
                result = load_file(cursor, path, snapshot)
                if previous:
                    cursor.execute(f"""
                        UPDATE {CHECKPOINT}
                        SET ContentSHA256 = ?, CompletedAtUTC = SYSUTCDATETIME()
                        WHERE SourceSystem = CONVERT(varchar(50), ?) AND RawFileName = ?
                    """, digest, source, path.name)
                else:
                    cursor.execute(f"""
                        INSERT INTO {CHECKPOINT} (SourceSystem, RawFileName, ContentSHA256)
                        VALUES (?, ?, ?)
                    """, source, path.name, digest)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            totals[0] += 1
            print(f"{path.name}: committed RAW counts={result}")
    print(f"RAW files processed={totals[0]}, unchanged={totals[1]}")
    return tuple(totals)


def run_incremental(raw_dir, pattern, source, get_connection, load_file):
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", metavar="FILENAME", help="Reprocess one named snapshot explicitly.")
    args = parser.parse_args()
    enabled = os.environ.get("JOBMARKET_RAW_INCREMENTAL") == "1"
    if not enabled and not args.replay:
        return False
    paths = sorted(raw_dir.glob(pattern))
    if args.replay:
        paths = [path for path in paths if path.name == args.replay]
        if not paths:
            parser.error("Replay requires the exact filename of a snapshot for this source.")
    if paths:
        with closing(get_connection()) as connection:
            ingest_files(connection, source, paths, load_file, replay=bool(args.replay))
    return True
