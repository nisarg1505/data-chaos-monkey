"""M1: Target Loader — parse a dbt project into injectable targets + a guard map."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import sqlglot
from sqlglot import exp


@dataclass
class Column:
    table: str  # model name, e.g. "stg_charges"
    name: str  # column name, e.g. "status"
    guarding_tests: list[str] = field(default_factory=list)

    @property
    def is_guarded(self) -> bool:
        return len(self.guarding_tests) > 0


@dataclass
class Project:
    columns: dict[str, Column]  # key: "table.column"
    lineage: dict[str, list[str]] = field(
        default_factory=dict
    )  # model -> upstream cols it reads


def load_manifest(manifest_path: str | Path) -> dict:
    with open(manifest_path) as f:
        return json.load(f)


def build_guard_map(manifest: dict) -> dict[str, Column]:
    """Extract every model column + which tests guard it, from manifest.json."""
    columns: dict[str, Column] = {}

    # 1. every column declared on a model (from schema.yml, surfaced in manifest)
    for node in manifest["nodes"].values():
        if node["resource_type"] != "model":
            continue
        table = node["name"]
        for col_name in node.get("columns", {}):
            columns[f"{table}.{col_name}"] = Column(table=table, name=col_name)

    # 2. attach tests to the columns they guard
    for node in manifest["nodes"].values():
        if node["resource_type"] != "test":
            continue
        # a generic test's column is in test_metadata / attached_node
        meta = node.get("test_metadata") or {}
        test_name = meta.get(
            "name", node["name"]
        )  # e.g. not_null, unique, accepted_values
        col_name = (meta.get("kwargs") or {}).get("column_name")
        # find which model this test attaches to
        depends = node.get("depends_on", {}).get("nodes", [])
        model_names = [
            manifest["nodes"][d]["name"]
            for d in depends
            if d in manifest["nodes"]
            and manifest["nodes"][d]["resource_type"] == "model"
        ]
        for model in model_names:
            if col_name:
                key = f"{model}.{col_name}"
                if key in columns:
                    columns[key].guarding_tests.append(test_name)

    return columns


def build_lineage_map(manifest: dict) -> dict[str, list[str]]:
    """AST-aware mapping of Model -> [Upstream Columns Consumed]."""
    lineage = {}

    for node in manifest["nodes"].values():
        if node["resource_type"] != "model":
            continue

        model_name = node["name"]
        # Requires compiled SQL (dbt compile) to resolve {{ ref() }} macros
        sql = node.get("compiled_code")
        if not sql:
            continue

        try:
            # Parse the raw AST using duckdb dialect
            ast = sqlglot.parse_one(sql, read="duckdb")

            # Extract every column referenced in the SELECT, WHERE, JOINs, etc.
            # Set comprehension deduplicates the column names.
            consumed_cols = list({col.name for col in ast.find_all(exp.Column)})
            lineage[model_name] = consumed_cols

        except sqlglot.errors.ParseError:
            # Fallback for heavily templated raw queries that break the parser
            lineage[model_name] = []

    return lineage


def load_project(manifest_path: str | Path) -> Project:
    manifest = load_manifest(manifest_path)
    columns = build_guard_map(manifest)
    lineage = build_lineage_map(manifest)
    return Project(columns=columns, lineage=lineage)
