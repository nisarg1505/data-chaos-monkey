"""Silent type coercion: lossy roundtrip that preserves the declared type
but destroys precision. FLOAT->INT->FLOAT truncates decimals; TIMESTAMP->
DATE->TIMESTAMP drops time-of-day. Passes not_null/unique/accepted_values.

Type-aware: raises for column types with no lossy op, so the sweep skips
instead of guessing (never confidently wrong). If values are already lossless
under the roundtrip (all-integral floats, midnight timestamps), the verdict
engine correctly reports NO-OP."""

from chaos_monkey.faults.base import Fault, FaultResult

_LOSSY_OPS = {
    "DOUBLE": "CAST(CAST({col} AS BIGINT) AS DOUBLE)",
    "FLOAT": "CAST(CAST({col} AS BIGINT) AS FLOAT)",
    "DECIMAL": "CAST(CAST({col} AS BIGINT) AS DOUBLE)",
    "TIMESTAMP": "CAST(CAST({col} AS DATE) AS TIMESTAMP)",
    "TIMESTAMP WITH TIME ZONE": "CAST(CAST({col} AS DATE) AS TIMESTAMPTZ)",
}


class TypeCoercion(Fault):
    name = "type_coercion"
    applies_to = {"numeric", "timestamp"}

    def _column_type(self, con, table, column):
        schema, tbl = table.split(".") if "." in table else ("main", table)
        row = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? AND column_name = ?",
            [schema, tbl, column],
        ).fetchone()
        if row is None:
            raise ValueError(f"column not found: {table}.{column}")
        return row[0].upper()

    def apply(self, con, table, column, severity):
        col_type = self._column_type(con, table, column)
        base_type = col_type.split("(")[0].strip()  # DECIMAL(18,2) -> DECIMAL
        op = _LOSSY_OPS.get(base_type)
        if op is None:
            raise ValueError(
                f"type_coercion has no lossy op for {col_type} ({table}.{column})"
            )
        expr = op.format(col=column)
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        n = max(1, int(total * severity))
        con.execute(f"""
            UPDATE {table}
            SET {column} = {expr}
            WHERE rowid IN (
                SELECT rowid FROM {table} ORDER BY rowid LIMIT {n}
            )
        """)
        return FaultResult(
            table=table,
            column=column,
            description=f"lossy roundtrip on {n}/{total} rows of "
            f"{column} ({col_type}: {expr})",
            rows_affected=n,
        )

    def suggested_test(self, column):
        return f"exact-value / dbt_utils.accepted_range test on {column}"
