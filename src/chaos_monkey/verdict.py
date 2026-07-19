"""M5: classify a fault's outcome. Never confidently wrong."""

import duckdb


def classify(run_result, clone_path, before_value, after_query):
    """
    run_result: dict from Runner (run_errors, test_failures)
    before_value: the output metric BEFORE injection
    after_query: SQL to measure the same metric on the clone AFTER
    Returns one of: CRASHED / CAUGHT / SILENT / NO-OP
    """
    con = duckdb.connect(clone_path)
    try:
        after = con.execute(after_query).fetchone()[0]
    finally:
        con.close()

    if run_result["run_errors"]:
        return "CRASHED", after
    if run_result["test_failures"]:
        return "CAUGHT", after
    if after != before_value:
        return "SILENT", after  # ran green but output changed
    return "NO-OP", after  # fault didn't actually change anything
