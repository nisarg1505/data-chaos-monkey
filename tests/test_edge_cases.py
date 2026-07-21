"""Pressure tests for the tool's OWN failure modes — not the faults, but what
happens when the tool meets conditions it wasn't happy-path designed for.

These exist because 'never confidently wrong' is only credible if the tool
behaves predictably at the edges: empty outputs, unusual types, a run that
errors, and the checksum's core guarantees. A senior reviewer will ask
'what breaks?' — these answer it.
"""

import duckdb
import pytest

from chaos_monkey.verdict import checksum, classify, get_checksum
from chaos_monkey.faults import get_fault


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "edge.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE main.out AS SELECT i AS id, i * 1.0 AS val FROM range(20) t(i)"
    )
    con.close()
    return path


# ---------------------------------------------------------------------------
# Verdict precedence: a run error outranks output change (CRASHED > SILENT)
# ---------------------------------------------------------------------------
def test_crash_outranks_silent(db):
    before = get_checksum(db, "main.out")
    con = duckdb.connect(db)
    con.execute("UPDATE main.out SET val = val + 1")  # output DID change
    con.close()
    # ...but the run also errored — must report CRASHED, not SILENT
    rr = {"run_errors": [{"unique_id": "model.x"}], "test_failures": []}
    verdict, _ = classify(rr, db, before, "main.out")
    assert verdict == "CRASHED"


# ---------------------------------------------------------------------------
# Empty output table: checksum is 0 (not NULL/crash), verdict is NO-OP
# ---------------------------------------------------------------------------
def test_empty_output_is_no_op_not_crash(tmp_path):
    path = str(tmp_path / "empty.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE main.out (id INTEGER, val DOUBLE)")  # no rows
    con.close()
    before = get_checksum(path, "main.out")
    assert before == 0  # COALESCE guard: empty -> 0, never NULL
    rr = {"run_errors": [], "test_failures": []}
    verdict, after = classify(rr, path, before, "main.out")
    assert verdict == "NO-OP" and after == 0


# ---------------------------------------------------------------------------
# Checksum is order-independent: same rows, different physical order -> equal
# ---------------------------------------------------------------------------
def test_checksum_ignores_row_order(tmp_path):
    path = str(tmp_path / "order.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE a AS SELECT * FROM range(50) t(i)")
    con.execute("CREATE TABLE b AS SELECT * FROM range(50) t(i) ORDER BY i DESC")
    ca, cb = checksum(con, "a"), checksum(con, "b")
    con.close()
    assert ca == cb


# ---------------------------------------------------------------------------
# Checksum is sensitive: a single cell change flips it
# ---------------------------------------------------------------------------
def test_checksum_detects_single_cell(tmp_path):
    # Use an explicit DOUBLE so the column can hold a small delta; range()*1.0
    # infers DECIMAL(2,1) in DuckDB, which would round the change away.
    path = str(tmp_path / "cell.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE main.out AS "
        "SELECT i AS id, CAST(i AS DOUBLE) AS val FROM range(20) t(i)"
    )
    con.close()
    c1 = get_checksum(path, "main.out")
    con = duckdb.connect(path)
    con.execute("UPDATE main.out SET val = val + 0.0001 WHERE id = 7")
    con.close()
    c2 = get_checksum(path, "main.out")
    assert c1 != c2


# ---------------------------------------------------------------------------
# NULL handling: a table full of NULLs still checksums deterministically,
# and differs from the same table with values (no silent NULL collision)
# ---------------------------------------------------------------------------
def test_null_rows_checksum_distinctly(tmp_path):
    path = str(tmp_path / "nulls.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE n AS SELECT i AS id, CAST(NULL AS DOUBLE) AS v FROM range(10) t(i)"
    )
    con.execute("CREATE TABLE m AS SELECT i AS id, 1.0 AS v FROM range(10) t(i)")
    cn1, cn2 = checksum(con, "n"), checksum(con, "n")
    cm = checksum(con, "m")
    con.close()
    assert cn1 == cn2  # deterministic
    assert cn1 != cm  # nulls not confused with values


# ---------------------------------------------------------------------------
# type_coercion refuses a non-coercible type rather than guessing
# (the 'never confidently wrong' contract, re-asserted at the edge)
# ---------------------------------------------------------------------------
def test_type_coercion_refuses_non_numeric(db):
    con = duckdb.connect(db)
    con.execute("ALTER TABLE main.out ADD COLUMN label VARCHAR")
    con.execute("UPDATE main.out SET label = 'x'")
    with pytest.raises(ValueError):
        get_fault("type_coercion").apply(con, "main.out", "label", 0.5)
    con.close()


# ---------------------------------------------------------------------------
# A fault applied to a single-row table still behaves (min-severity clamp
# means at least one row is affected, never zero-by-rounding)
# ---------------------------------------------------------------------------
def test_fault_on_single_row_table(tmp_path):
    # min-severity clamp: even severity*rows rounding to 0 must affect >= 1 row.
    path = str(tmp_path / "one.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE main.t AS SELECT 1 AS id, CAST(5.0 AS DOUBLE) AS amount")
    r = get_fault("unit_shift").apply(con, "main.t", "amount", 0.3, factor=1000)
    assert r.rows_affected >= 1
    con.close()


def test_unit_shift_overflow_raises_not_silently_wrong(tmp_path):
    # A tight fixed-precision column can't hold value*factor. The tool must
    # RAISE (surfaced downstream as CRASHED) rather than silently truncate —
    # a wrong-but-green result would violate 'never confidently wrong'.
    path = str(tmp_path / "tight.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE main.t AS SELECT 1 AS id, CAST(5.0 AS DECIMAL(2,1)) AS amount"
    )
    with pytest.raises(Exception):
        get_fault("unit_shift").apply(con, "main.t", "amount", 1.0, factor=1000)
    con.close()
