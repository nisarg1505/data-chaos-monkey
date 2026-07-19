"""Statistical drift: set a fraction of a column's values to NULL."""

from chaos_monkey.faults.base import Fault, FaultResult


class StatisticalDrift(Fault):
    name = "statistical_drift"
    applies_to = {"any"}  # nulls can hit any column

    def apply(self, con, table: str, column: str, severity: float) -> FaultResult:
        # severity = fraction of rows to null out (e.g. 0.3 = 30%)
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
        # null out the first n rows deterministically (by rowid) for reproducibility
        con.execute(f"""
            UPDATE {table}
            SET {column} = NULL
            WHERE rowid IN (
                SELECT rowid FROM {table} ORDER BY rowid LIMIT {n}
            )
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"set {n}/{total} rows of {column} to NULL ({severity:.0%})",
            rows_affected=n,
        )

    def suggested_test(self, column: str) -> str:
        return f"not_null test on {column}"
