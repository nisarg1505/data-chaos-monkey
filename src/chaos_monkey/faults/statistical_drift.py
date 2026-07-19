from chaos_monkey.faults.base import Fault, FaultResult


class StatisticalDrift(Fault):
    name = "statistical_drift"
    applies_to = {"any"}

    def apply(self, con, table, column, severity):
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
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

    def suggested_test(self, column):
        return f"not_null test on {column}"
