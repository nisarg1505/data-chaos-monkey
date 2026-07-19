"""M3 (DuckDB slice): safely inject a fault into an isolated copy of the data."""

import shutil
from pathlib import Path


def clone_db(source_db: str, clone_path: str) -> str:
    """Zero-effort clone on DuckDB: copy the .duckdb file. Prod stays untouched."""
    shutil.copy(source_db, clone_path)
    return clone_path


def verify_untouched(source_db: str, expected_size: int) -> bool:
    """Safety check: the source file must be unchanged after a run."""
    return Path(source_db).stat().st_size == expected_size
