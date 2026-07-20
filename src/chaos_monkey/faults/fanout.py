"""Fanout: duplicate rows to break an assumed 1:1 join grain.
Exact-copy duplicates — only cardinality breaks, not values — so downstream
aggregates silently inflate unless a unique test guards the key."""

from chaos_monkey.faults.base import Fault, FaultResult


class Fanout(Fault):
    name = "fanout"
    applies_to = {"any"}

    def apply(self, con, table, column, severity):
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * min(severity, 0.1)))
        con.execute(f"""
            INSERT INTO {table}
            SELECT * FROM {table} ORDER BY rowid LIMIT {n}
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"duplicated {n}/{total} rows (grain break on {column})",
            rows_affected=n,
        )

    def suggested_test(self, column):
        return f"unique test on {column}"
