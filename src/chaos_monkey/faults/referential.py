"""Referential drift: rewrite FK values to nonexistent keys.
Caught only by relationships tests; otherwise downstream INNER JOINs
silently drop rows or LEFT JOINs produce NULL-enriched garbage."""

from chaos_monkey.faults.base import Fault, FaultResult


class Referential(Fault):
    name = "referential"
    applies_to = {"string"}

    def apply(self, con, table, column, severity, ghost_prefix="ghost_"):
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
        con.execute(f"""
            UPDATE {table}
            SET {column} = '{ghost_prefix}' || {column}
            WHERE rowid IN (
                SELECT rowid FROM {table} ORDER BY rowid LIMIT {n}
            )
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"orphaned {n}/{total} rows of {column} "
            f"(prefixed '{ghost_prefix}')",
            rows_affected=n,
        )

    def suggested_test(self, column):
        return f"relationships test on {column}"
