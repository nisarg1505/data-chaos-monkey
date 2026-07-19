"""Enum drift: replace a column's values with an unseen category."""

from chaos_monkey.faults.base import Fault, FaultResult


class EnumDrift(Fault):
    name = "enum_drift"
    applies_to = {"string"}

    def apply(self, con, table, column, severity, new_value="processing"):
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
        con.execute(f"""
            UPDATE {table}
            SET {column} = '{new_value}'
            WHERE rowid IN (
                SELECT rowid FROM {table} ORDER BY rowid LIMIT {n}
            )
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"set {n}/{total} rows of {column} to '{new_value}'",
            rows_affected=n,
        )

    def suggested_test(self, column):
        return f"accepted_values test on {column}"
