"""M3: safely clone the pipeline db and inject a fault into the SOURCE table."""

import shutil
from pathlib import Path
import duckdb


class Injector:
    def __init__(self, source_db: str, clone_path: str = "/tmp/chaos_clone.duckdb"):
        self.source_db = source_db
        self.clone_path = clone_path

        # Guarantee all unwritten WAL data is flushed to the main file before we read metadata
        self._checkpoint_source()

        # st_mtime (modification time) is strictly safer than st_size
        self._source_mtime = Path(source_db).stat().st_mtime

    def _checkpoint_source(self):
        """Forces DuckDB to flush the WAL so the single .duckdb file is fully consistent."""
        con = duckdb.connect(self.source_db)
        try:
            con.execute("FORCE CHECKPOINT;")
        finally:
            con.close()

    def clone(self):
        """Zero-effort clone: copy the db file. Source is never touched."""
        shutil.copy(self.source_db, self.clone_path)
        return self.clone_path

    def inject(self, fault, table, column, severity):
        """Apply a fault to the clone. Returns the FaultResult."""
        con = duckdb.connect(self.clone_path)
        try:
            result = fault.apply(con, table, column, severity)
        finally:
            con.close()  # release so dbt can open it
        return result

    def verify_source_untouched(self) -> bool:
        """Safety guarantee: the source file must not have been modified."""
        return Path(self.source_db).stat().st_mtime == self._source_mtime
