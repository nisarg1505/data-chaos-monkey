"""Unit shift: multiply a numeric column by a constant (sec->ms, pct->ratio).
The classic silent killer: passes not_null, unique, and type checks."""

from chaos_monkey.faults.base import Fault, FaultResult


class UnitShift(Fault):
    name = "unit_shift"
    applies_to = {"numeric"}

    def apply(self, con, table, column, severity, factor=1000):
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
        con.execute(f"""
            UPDATE {table}
            SET {column} = {column} * {factor}
            WHERE rowid IN (
                SELECT rowid FROM {table} ORDER BY rowid LIMIT {n}
            )
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"multiplied {n}/{total} rows of {column} by {factor}",
            rows_affected=n,
        )

    def suggested_test(self, column):
        return f"dbt_utils.accepted_range test on {column}"
