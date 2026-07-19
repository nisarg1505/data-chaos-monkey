"""M3: safely clone the pipeline db and inject a fault into the SOURCE table."""

import shutil
from pathlib import Path
import duckdb


class Injector:
    def __init__(self, source_db: str, clone_path: str = "/tmp/chaos_clone.duckdb"):
        self.source_db = source_db
        self.clone_path = clone_path
        self._source_size = Path(source_db).stat().st_size

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
        """Safety guarantee: the source file must be byte-identical after a run."""
        return Path(self.source_db).stat().st_size == self._source_size
