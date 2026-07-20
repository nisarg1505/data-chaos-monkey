"""M4 / H1.2: re-run the pipeline on the corrupted clone, scoped to the
affected subgraph.

Two-pass design (critical for correctness):
  Pass 1 (build): rebuild ONLY downstream models, excluding the injected
                  model so the corruption survives the rebuild.
  Pass 2 (test):  run the injected model's OWN tests against the corrupted
                  data — these are exactly the guards that should fire.

A single `dbt build --exclude <model>` drops both the model AND its attached
tests, so the guards never run and every fault looks SILENT. Splitting build
from test is what lets CAUGHT be detected. Each dbt invocation overwrites
run_results.json, so we parse after each pass and merge in memory.
"""

import json
import subprocess
from pathlib import Path


class Runner:
    def __init__(self, dbt_dir: str, target: str = "clone"):
        self.dbt_dir = dbt_dir
        self.target = target

    def _dbt(self, verb: str, select=None, exclude=None):
        cmd = [
            "uv",
            "run",
            "dbt",
            verb,
            "--profiles-dir",
            ".",
            "--target",
            self.target,
        ]
        if select:
            cmd += ["--select", select]
        if exclude:
            cmd += ["--exclude", exclude]
        subprocess.run(cmd, cwd=self.dbt_dir, capture_output=True, text=True)
        return self._parse_results()

    def run(self, select=None, exclude=None, exclude_seed=True):
        """Re-run the pipeline on the clone and return merged results.

        select:  dbt --select expression (e.g. 'stg_events+') to prune the DAG.
        exclude: the injected model, skipped in the build pass so corruption
                 survives, then tested in the test pass.
        """
        # --- Pass 1: build downstream models, skip the injected model ---
        build_exclusions = []
        if exclude:
            build_exclusions.append(exclude)
        if exclude_seed:
            build_exclusions.append("resource_type:seed")
        build_res = self._dbt(
            "build",
            select=select,
            exclude=" ".join(build_exclusions) or None,
        )

        # --- Pass 2: run the injected model's own tests on corrupted data ---
        # Only meaningful when we excluded a model from the build.
        test_res = {"run_errors": [], "test_failures": []}
        if exclude:
            test_res = self._dbt("test", select=exclude)

        # --- Merge (a failure/error in EITHER pass counts) ---
        return {
            "run_errors": build_res["run_errors"] + test_res["run_errors"],
            "test_failures": build_res["test_failures"] + test_res["test_failures"],
        }

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
