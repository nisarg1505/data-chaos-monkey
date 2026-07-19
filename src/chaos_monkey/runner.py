"""M4: re-run the dbt pipeline against the corrupted clone, capture results."""

import json
import subprocess
from pathlib import Path


class Runner:
    def __init__(self, dbt_dir: str, target: str = "clone"):
        self.dbt_dir = dbt_dir
        self.target = target

    def run(self):
        """Rebuild models + tests on the clone. --exclude the seed so the
        injected corruption in the source table survives (dbt build re-seeds
        from the clean CSV otherwise)."""
        subprocess.run(
            [
                "uv",
                "run",
                "dbt",
                "build",
                "--profiles-dir",
                ".",
                "--target",
                self.target,
                "--exclude",
                "raw_charges",
            ],
            cwd=self.dbt_dir,
            capture_output=True,
            text=True,
        )
        return self._parse_results()

    def _parse_results(self):
        path = Path(self.dbt_dir) / "target" / "run_results.json"
        with open(path) as f:
            results = json.load(f)["results"]
        return {
            "run_errors": [r for r in results if r["status"] == "error"],
            "test_failures": [
                r
                for r in results
                if r["status"] == "fail" and r["unique_id"].startswith("test.")
            ],
        }
