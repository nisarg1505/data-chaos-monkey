# Context prompt — paste into a fresh Claude to get build help

Copy everything in the block below into a new Claude conversation. It gives Claude the full picture so it can give you concrete, correct build instructions without re-litigating decisions you've already made.

---

```
You are helping me build a specific software project. Everything below is DECIDED —
do not re-open these decisions or suggest alternative projects. Help me BUILD it:
give concrete, step-by-step instructions, real code, and debugging help. Be blunt,
dense, and practical. Tables and code over prose. Assume I'm a senior-track data
engineer on a MacBook M4 Pro.

## THE PROJECT: "Data Chaos Monkey"
Chaos engineering for DATA, not infrastructure. Existing chaos tools (Chaos Mesh,
Gremlin, AWS FIS) attack pods/networks. Nobody attacks the data itself. My tool
injects realistic, subtle data corruptions into a CLONED data pipeline and measures
whether the pipeline's existing tests actually catch them — then reports a
resilience score and the exact faults that reach the output SILENTLY.

Positioning: "Everyone builds the fire alarm (observability like Monte Carlo). I
built the fire drill — it proves your data detection actually works BEFORE a real
incident." It's a test-suite auditor that works by controlled sabotage.

Goal: a portfolio project that impresses a senior engineer / hiring manager when I
EXPLAIN it (not an adoption/startup play). The build being genuinely hard + working
+ legible is the point. NOT chasing novelty or stars.

## THE GOVERNING RULE
"Never confidently wrong." The tool may say "config unavailable" or "pipeline
non-deterministic — verdict unreliable," but must NEVER blame the wrong axis or
falsely flag a silent fault. A fault counts as SILENT only if it BOTH passed all
tests AND measurably changed the output vs a clean baseline. For a trust tool, a
confident wrong answer is the only unforgivable failure.

## ARCHITECTURE (6 components)
1. Target Loader — parse dbt manifest/sources; sqlglot for column-level lineage
   (which columns the failing model consumes + which tests guard which columns).
2. Fault Catalog — library of realistic, parameterized, reversible corruptions.
3. Safe Injector — zero-copy CLONE the data, apply ONE fault to the clone, NEVER
   prod. (This safety model is the whole unlock — data-chaos made safe.)
4. Pipeline Runner — run the pipeline on the corrupted clone, scoped to the
   affected subgraph (not full DAG), capture run_results.json.
5. Verdict Engine — classify each fault: CAUGHT (a test fired) / SILENT (ran green
   but output changed) / CRASHED (schema/SQL error). Cross-check SILENT against a
   clean baseline output diff.
6. Resilience Report — score + list of SILENT faults + the specific test that would
   catch each.

## STACK
- dbt Core + dbt-duckdb (pipeline under test; DuckDB = zero-infra local runs on M4)
- sqlglot (parse models, column-level lineage, AST-aware analysis)
- duckdb + pandas (fault injection + profiling locally)
- click (CLI: `chaos-monkey run`), rich (pretty terminal report = the v1 "UI")
- Python managed by uv; pytest + ruff + pre-commit
- Snowflake added LATER only for the demo stage (zero-copy clone story). v1 is
  100% local on DuckDB.

## v1 SCOPE (what I'm building now)
- CLI tool (no product UI — dashboards/settings are explicitly OUT of scope).
- 3 fault classes only: statistical null-drift, enum-drift, silent type-coercion.
- Clone-based safety (prod checksum-identical before/after).
- One hosted interactive demo page built LAST (the "green suite but silently
  broken" reveal) — thin visual skin over the working CLI.
- Deterministic pipelines assumed (non-determinism muddies the caught/silent verdict).

## MILESTONES (empty repo -> shippable)
M0 fixture (breakable dbt project + a GROUND-TRUTH table of which columns are
   guarded vs unguarded — the answer key that proves the tool is correct)
M1 loader (sqlglot lineage) → M2 fault catalog (3 faults) → M3 safe injector
(clone) → M4 runner (scoped, run_results.json) → M5 verdict engine (caught/silent/
crashed) → M6 resilience report → M7 money-shot demo → M8 ship + live demo page

## KEY BUILD DISCIPLINES
- M0 first, and its GROUND-TRUTH table is the most important early artifact — every
  later verdict is validated against it. A chaos tool without a ground-truth fixture
  only HOPES it's right.
- One fault flowing end-to-end (inject → run → correct verdict) beats ten shaky
  faults. Don't widen the catalog or touch the demo until one fault works fully.
- The two components that ARE the product: M3 (safe injection) and M5 (the verdict).
  Build the plumbing fast; spend the best effort there and on M7's reveal.
- Repo scaffold: src/chaos_monkey/{cli,loader,injector,runner,verdict,report}.py +
  faults/{base,statistical_drift,enum_drift,type_coercion}.py; fixture/ holds M0.

## WHERE I AM RIGHT NOW
[EDIT THIS LINE before pasting: e.g. "Setup done (brew/git/uv/deps installed, repo
cloned + pushed). About to build M0." or "M0 done, starting M1." etc.]

Given all that, help me with: [EDIT: your specific ask, e.g. "walk me through M1 —
writing the sqlglot loader that maps columns to the tests guarding them."]
```

---

## How to use this
1. Copy the block above into a fresh Claude conversation.
2. **Edit the two `[EDIT]` lines** — "where I am" and "what I need help with."
3. Ask away. Because the decisions are locked in the prompt, Claude will help you
   *build* instead of re-debating the idea.

## Tip
Keep this file (`DataChaosMonkey_ContextPrompt.md`) in your repo. Each time you
start a new Claude session for a new milestone, paste the block, update the two
edit lines, and go. It's your reusable "load context" command.
