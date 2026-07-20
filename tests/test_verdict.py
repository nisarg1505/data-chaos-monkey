"""Truth table for classify(). The verdict IS the product, so this is the
most important test file. classify() is pure over (run_result, checksums),
so we mock run_result as a plain dict and drive a real DuckDB clone for the
before/after checksum.

Precedence under test: CRASHED > CAUGHT > SILENT > NO-OP.
"""

import duckdb
import pytest

from chaos_monkey.verdict import classify, get_checksum, checksum


@pytest.fixture
def clone(tmp_path):
    """A tiny real DuckDB file with an output table we can mutate."""
    path = str(tmp_path / "clone.duckdb")
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE main.out AS SELECT i AS id, i * 1.0 AS val FROM range(10) t(i)"
    )
    con.close()
    return path


def _mutate_output(clone_path):
    con = duckdb.connect(clone_path)
    con.execute("UPDATE main.out SET val = val + 1 WHERE id = 0")
    con.close()


# --- precedence: a run error wins even if output also changed -------------
def test_crashed_beats_everything(clone):
    before = get_checksum(clone, "main.out")
    _mutate_output(clone)  # output changed too, but run errored
    run_result = {"run_errors": [{"unique_id": "model.x"}], "test_failures": []}
    verdict, _ = classify(run_result, clone, before, "main.out")
    assert verdict == "CRASHED"


# --- a firing test => CAUGHT, even if output changed ----------------------
def test_caught_when_test_fails(clone):
    before = get_checksum(clone, "main.out")
    _mutate_output(clone)
    run_result = {"run_errors": [], "test_failures": [{"unique_id": "test.y"}]}
    verdict, _ = classify(run_result, clone, before, "main.out")
    assert verdict == "CAUGHT"


# --- green run + changed output => SILENT (the money verdict) --------------
def test_silent_when_green_but_output_changed(clone):
    before = get_checksum(clone, "main.out")
    _mutate_output(clone)
    run_result = {"run_errors": [], "test_failures": []}
    verdict, after = classify(run_result, clone, before, "main.out")
    assert verdict == "SILENT"
    assert after != before


# --- green run + identical output => NO-OP (fault didn't bite) -------------
def test_no_op_when_output_unchanged(clone):
    before = get_checksum(clone, "main.out")
    # no mutation
    run_result = {"run_errors": [], "test_failures": []}
    verdict, after = classify(run_result, clone, before, "main.out")
    assert verdict == "NO-OP"
    assert after == before


# --- checksum is order-independent (guards the SUM(hash) design) ----------
def test_checksum_order_independent(tmp_path):
    path = str(tmp_path / "order.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE a AS SELECT * FROM range(5) t(i)")
    con.execute("CREATE TABLE b AS SELECT * FROM range(5) t(i) ORDER BY i DESC")
    ca, cb = checksum(con, "a"), checksum(con, "b")
    con.close()
    assert ca == cb


# --- empty table checksum is 0, not NULL (COALESCE guard) -----------------
def test_empty_table_checksum_is_zero(tmp_path):
    path = str(tmp_path / "empty.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE e (id INTEGER)")
    val = checksum(con, "e")
    con.close()
    assert val == 0
