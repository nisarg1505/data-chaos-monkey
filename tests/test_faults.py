"""Each fault must (1) actually change the target when it applies, and
(2) refuse cleanly when it can't (type_coercion on a string) rather than
guess. 'Never confidently wrong' starts here.
"""

import duckdb
import pytest

from chaos_monkey.faults import get_fault, applicable_faults, REGISTRY


@pytest.fixture
def con(tmp_path):
    """Fresh table with numeric, string, and timestamp columns."""
    path = str(tmp_path / "f.duckdb")
    c = duckdb.connect(path)
    c.execute("""
        CREATE TABLE main.ev AS
        SELECT i AS id,
               'user_' || i AS actor,
               i * 1.5 AS amount,
               TIMESTAMP '2026-01-01 10:30:00' + INTERVAL (i) HOUR AS ts
        FROM range(100) t(i)
    """)
    yield c
    c.close()


def _snapshot(con):
    return con.execute(
        "SELECT count(*), sum(amount), min(actor), min(ts) FROM main.ev"
    ).fetchone()


# ---- every registered fault exposes name + suggested_test ----------------
@pytest.mark.parametrize("name", list(REGISTRY))
def test_fault_contract(name):
    f = get_fault(name)
    assert f.name == name
    assert isinstance(f.suggested_test("col"), str)
    assert isinstance(f.applies_to, set)


# ---- faults that apply actually change the table -------------------------
@pytest.mark.parametrize(
    "name,column",
    [
        ("statistical_drift", "amount"),
        ("enum_drift", "actor"),
        ("unit_shift", "amount"),
        ("fanout", "id"),
        ("referential", "actor"),
        ("type_coercion", "amount"),
        ("type_coercion", "ts"),
    ],
)
def test_fault_mutates(con, name, column):
    before = _snapshot(con)
    result = get_fault(name).apply(con, "main.ev", column, 0.3)
    after = _snapshot(con)
    assert result.rows_affected > 0
    assert before != after, f"{name}({column}) produced no observable change"


# ---- specific signatures (guards against a fault silently no-op'ing) -----
def test_unit_shift_scales(con):
    before = con.execute("SELECT sum(amount) FROM main.ev").fetchone()[0]
    get_fault("unit_shift").apply(con, "main.ev", "amount", 0.3, factor=1000)
    after = con.execute("SELECT sum(amount) FROM main.ev").fetchone()[0]
    assert after > before * 50  # 30% of rows ×1000 dominates the total


def test_fanout_adds_rows(con):
    before = con.execute("SELECT count(*) FROM main.ev").fetchone()[0]
    get_fault("fanout").apply(con, "main.ev", "id", 0.3)
    after = con.execute("SELECT count(*) FROM main.ev").fetchone()[0]
    assert after == before + 30


def test_referential_orphans_keys(con):
    get_fault("referential").apply(con, "main.ev", "actor", 0.3)
    orphans = con.execute(
        "SELECT count(*) FROM main.ev WHERE actor LIKE 'ghost_%'"
    ).fetchone()[0]
    assert orphans == 30


def test_type_coercion_truncates_timestamp(con):
    get_fault("type_coercion").apply(con, "main.ev", "ts", 1.0)
    # every ts now at midnight -> no non-midnight rows remain
    non_midnight = con.execute(
        "SELECT count(*) FROM main.ev WHERE ts != date_trunc('day', ts)"
    ).fetchone()[0]
    assert non_midnight == 0


# ---- refusal path: type_coercion must not guess on a string --------------
def test_type_coercion_refuses_string(con):
    with pytest.raises(ValueError, match="no lossy op"):
        get_fault("type_coercion").apply(con, "main.ev", "actor", 0.3)


def test_type_coercion_refuses_missing_column(con):
    with pytest.raises(ValueError, match="column not found"):
        get_fault("type_coercion").apply(con, "main.ev", "nope", 0.3)


# ---- type-family filter routes faults correctly --------------------------
@pytest.mark.parametrize(
    "family,must_include,must_exclude",
    [
        ("numeric", "unit_shift", "enum_drift"),
        ("string", "referential", "unit_shift"),
        ("timestamp", "type_coercion", "enum_drift"),
        ("other", "fanout", "type_coercion"),
    ],
)
def test_applicable_faults_filter(family, must_include, must_exclude):
    allowed = applicable_faults(family)
    assert must_include in allowed
    assert must_exclude not in allowed


def test_applicable_faults_any_returns_all():
    assert set(applicable_faults("any")) == set(REGISTRY)


def test_unknown_fault_raises():
    with pytest.raises(ValueError, match="unknown fault"):
        get_fault("nonexistent")
