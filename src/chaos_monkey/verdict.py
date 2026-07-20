"""M5 / H1.1: classify a fault's outcome using dynamic table checksums.
Never confidently wrong."""

import duckdb


def checksum(con, table: str) -> int:
    """Structural checksum of an entire table. Any cell change -> different number.
    O(1) memory: DuckDB aggregates server-side."""
    # hash every row's full content, sum the hashes. Order-independent.
    row = con.execute(
        f"SELECT COALESCE(SUM(hash(CAST(t AS VARCHAR))), 0) FROM {table} t"
    ).fetchone()
    return row[0]


def get_checksum(clone_path: str, table: str) -> int:
    con = duckdb.connect(clone_path)
    try:
        return checksum(con, table)
    finally:
        con.close()


def classify(run_result, clone_path, before_checksum, output_table):
    """
    run_result: dict from Runner (run_errors, test_failures)
    before_checksum: checksum of output_table BEFORE injection
    output_table: the table whose corruption we measure (e.g. 'main.daily_metrics')
    Returns (verdict, after_checksum).
    """
    after = get_checksum(clone_path, output_table)

    if run_result["run_errors"]:
        return "CRASHED", after
    if run_result["test_failures"]:
        return "CAUGHT", after
    if after != before_checksum:
        return "SILENT", after  # ran green but output changed
    return "NO-OP", after  # fault didn't actually change output
