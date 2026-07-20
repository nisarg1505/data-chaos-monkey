"""M4 / H1.2: re-run the pipeline, scoped to only affected models."""

import json
import subprocess
from pathlib import Path


class Runner:
    def __init__(self, dbt_dir: str, target: str = "clone"):
        self.dbt_dir = dbt_dir
        self.target = target

    def run(self, select: str | None = None, exclude_seed: bool = True):
        """Rebuild models + tests on the clone.
        select: dbt --select expression (e.g. 'stg_events+') to prune the DAG.
                None = build everything (fallback).
        exclude_seed: skip seeds so injected corruption in source tables survives.
        """
        cmd = [
            "uv",
            "run",
            "dbt",
            "build",
            "--profiles-dir",
            ".",
            "--target",
            self.target,
        ]
        if select:
            cmd += ["--select", select]
        if exclude_seed:
            cmd += ["--exclude", "resource_type:seed"]
        subprocess.run(cmd, cwd=self.dbt_dir, capture_output=True, text=True)
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
