# Data Chaos Monkey — Project Setup (Day One)

> Get from empty directory → working scaffold you can run, on your M4 Pro, DuckDB-first. No Snowflake needed until the demo stage. M0 (the fixture) is your *first build task*, not part of setup — this doc gets you to the starting line.

---

## 0 · Prerequisites (verify first)

```bash
# macOS arm64 (M4 Pro) — check what you have
python3 --version      # need 3.11+
git --version
# install uv (fast python tooling) if missing:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

That's it for v1. No Docker, no Snowflake, no cloud account yet — everything runs local on DuckDB.

---

## 1 · Create the repo

```bash
mkdir data-chaos-monkey && cd data-chaos-monkey
git init
uv init --package --name chaos_monkey
```

---

## 2 · Dependencies

```bash
# core runtime
uv add dbt-core dbt-duckdb sqlglot pandas duckdb click rich
# dev tooling
uv add --dev pytest ruff pre-commit
# (Snowflake added LATER, at demo stage: uv add dbt-snowflake snowflake-connector-python)
```

Why each:
| Package | Role |
|---------|------|
| `dbt-core` + `dbt-duckdb` | the pipeline under test; DuckDB adapter = zero-infra local runs |
| `sqlglot` | parse models → find injectable columns + map tests to columns |
| `duckdb` / `pandas` | fault injection + profiling on local data |
| `click` | CLI framework (`chaos-monkey run ...`) |
| `rich` | pretty terminal resilience report (the v1 "UI") |
| `pytest` / `ruff` / `pre-commit` | tests, lint, hygiene |

---

## 3 · Repo structure (scaffold this now)

```
data-chaos-monkey/
├── README.md                  # start with the fire-drill positioning line
├── pyproject.toml             # uv-managed
├── Makefile                   # make demo / test / lint
├── .gitignore
├── .pre-commit-config.yaml
├── .env.example               # (empty for v1; Snowflake creds go here later)
│
├── src/chaos_monkey/
│   ├── __init__.py
│   ├── cli.py                 # click entrypoint: `chaos-monkey run`
│   ├── loader.py              # M1: parse manifest/sources, sqlglot lineage
│   ├── injector.py            # M3: clone + apply ONE fault (safe)
│   ├── runner.py              # M4: run pipeline on the clone, capture run_results
│   ├── verdict.py             # M5: caught / silent / crashed
│   ├── report.py              # M6: resilience score + suggested tests (rich)
│   └── faults/                # M2: the fault catalog
│       ├── __init__.py        # registry: name -> fault class
│       ├── base.py            # Fault ABC: applies_to, severity, apply(), describe()
│       ├── statistical_drift.py
│       ├── enum_drift.py
│       └── type_coercion.py
│
├── fixture/                   # M0 lives here (your FIRST build task, not setup)
│   └── dbt_project/           # the deliberately-breakable dbt project
│
├── tests/
│   └── test_faults.py         # unit-test each fault applies correctly
│
└── demo/                      # M8: the interactive page (built last)
```

Scaffold command:

```bash
mkdir -p src/chaos_monkey/faults fixture tests demo
touch src/chaos_monkey/{__init__,cli,loader,injector,runner,verdict,report}.py
touch src/chaos_monkey/faults/{__init__,base,statistical_drift,enum_drift,type_coercion}.py
touch tests/test_faults.py
```

---

## 4 · The Fault interface (define this first — it shapes everything)

`src/chaos_monkey/faults/base.py` — the contract every fault implements:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class FaultResult:
    table: str
    column: str
    description: str        # human-readable, for the report
    rows_affected: int

class Fault(ABC):
    name: str              # e.g. "statistical_drift"
    applies_to: set[str]   # column types this fault is valid for, e.g. {"numeric"}

    @abstractmethod
    def apply(self, con, table: str, column: str, severity: float) -> FaultResult:
        """Mutate ONLY the cloned table/column. Return what was done."""
        ...

    @abstractmethod
    def suggested_test(self, column: str) -> str:
        """The dbt test that WOULD catch this fault (for the report)."""
        ...
```

Getting this ABC right on day one means every fault, the injector, and the report all share one clean shape. Start here before writing any concrete fault.

---

## 5 · Makefile (the two commands you'll live in)

```makefile
.PHONY: demo test lint

demo:            ## run chaos on the fixture, print resilience report
	uv run chaos-monkey run --project fixture/dbt_project

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
```

---

## 6 · Config files

`.gitignore`:
```
.env
*.duckdb
fixture/dbt_project/target/
fixture/dbt_project/dbt_packages/
__pycache__/
.venv/
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks: [{id: ruff}, {id: ruff-format}]
```

```bash
uv run pre-commit install
```

---

## 7 · First commit

```bash
git add -A
git commit -m "scaffold: chaos-monkey skeleton, fault ABC, DuckDB-first"
```

---

## 8 · What "setup done" looks like

- [ ] `uv run chaos-monkey --help` prints (even if `run` is a stub)
- [ ] `make lint` and `make test` pass on the empty scaffold
- [ ] The Fault ABC is defined and one empty concrete fault imports cleanly
- [ ] pre-commit is installed
- [ ] First commit is in

**You are now at the start line. Next task = M0:** build the deliberately-breakable dbt fixture in `fixture/dbt_project/` with a *written ground-truth list* of which columns are guarded vs unguarded. (See the execution doc, M0.) Don't skip the ground-truth list — it's how you'll prove your verdicts are correct.

---

## Order of attack (first two weeks)
1. **Setup** (this doc) — half a day.
2. **M0 fixture** — the breakable pipeline + ground-truth list. ~2 days. *Most important early step.*
3. **M4 Fault ABC → one fault (statistical_drift)** end-to-end on the fixture, even before the injector is clean. Prove one fault works locally.
4. Then M1 loader → M3 injector → M5 verdict, in that order.

Resist building the fault catalog wide or touching the demo page until one fault flows end-to-end (inject → run → correct verdict) on the fixture. One proven fault beats ten shaky ones.
