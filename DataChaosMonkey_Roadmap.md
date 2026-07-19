# Data Chaos Monkey — Roadmap

> **Chaos engineering for your data, not your infrastructure.** Injects realistic, subtle corruptions into a *cloned* pipeline and proves which ones your tests (and later, your observability tools) actually catch — before a real incident.

**Positioning (lead with this):** *"Everyone's building the fire alarm. I built the fire drill — it proves your data detection actually works before the house is on fire."* Observability tells you when it's burning; Chaos Monkey proves your detection would fire *before* it does.

---

## The arc at a glance

| Version | Theme | Audits | Backend | Ships | Effort |
|---------|-------|--------|---------|-------|:------:|
| **v1** | The engine + the reveal | dbt tests / contracts | DuckDB (local) → Snowflake (demo) | CLI + one live demo page | ~10–14 wks |
| **v2** | The fire drill is literal | dbt tests **+ observability monitors** | + Snowflake native | "proves Monte Carlo actually fires" | +4–6 wks |
| **v3** | Continuous + diagnostic | scheduled runs + *where* faults are caught | multi-warehouse | monitor mode + attribution | +6–8 wks |

Build v1 to *done and shipped* before touching v2. Each version is standalone-impressive; v2/v3 are upside, not obligations.

---

## v1 — The Engine + The Reveal (the whole portfolio bar, on its own)

**Goal:** a working CLI that injects realistic faults into a cloned pipeline and reports which reach the output silently — plus one interactive demo page that makes the "green-but-silently-broken" moment visceral.

**What ships:**
- CLI: `chaos-monkey run` → terminal resilience report (caught / silent / crashed + score + suggested tests).
- 3 proven fault classes: statistical null-drift, enum-drift, silent type-coercion.
- Clone-based safety: faults only ever touch an isolated copy; prod is checksum-identical before/after.
- One hosted interactive page: click "inject fault" → watch pipeline run green → see corruption slip through silently.
- README with the money-shot GIF and the fire-drill positioning.

**This version alone clears "wow a resume reader."** Everything past here is bonus. Do not start v2 until v1 is shipped, demoed, and written up.

**Milestones:** `M0 fixture → M1 loader → M2 catalog(×3) → M3 safe injector → M4 runner → M5 verdict → M6 report → M7 money-shot → M8 ship + live demo`

**Definition of done:** a stranger opens your hosted page, injects a fault, and watches a green test suite let corrupted data through — and your README leads with "fire drill for your data."

---

## v2 — Make the Fire-Drill Claim Literal (the positioning becomes unassailable)

**Goal:** don't just audit *dbt tests* — audit the *observability layer* itself. Inject a fault, then check whether the observability tool (or a native freshness/anomaly monitor) actually raised an alert.

**Why it matters:** this converts the fire-drill line from metaphor to literal truth. You're no longer competing with Monte Carlo / Anomalo — you're the QA layer that *validates* them. "I inject a fault and prove whether your anomaly detection fires" is a claim no observability vendor can dismiss.

**What ships:**
- A monitor-verdict axis: for each fault, did an observability/freshness monitor fire? (caught-by-test / caught-by-monitor / silent).
- Support for at least one real detection layer (Snowflake native monitors, dbt source freshness, or an OSS anomaly check).
- Report now scores *both* your tests and your monitors.

**Scope discipline:** only start once v1 is fully shipped. This is the extension that makes the pitch complete, not a v1 requirement.

---

## v3 — Continuous + Diagnostic (the depth flex)

**Goal:** two upgrades that turn a point-in-time auditor into a system.

1. **Continuous monitor mode** — run the chaos suite on a schedule (or on every PR) so resilience is *tracked over time*, not checked once. Converts episodic value into continuous value.
2. **Diagnostic mode (the attribution engine)** — when a fault *is* caught, show *where* and *why* it was caught; when a real break happens, reuse the same clone machinery to bisect code-vs-data-vs-config. This is the "This Used to Work" tool folded in as the diagnostic half — offensive tool + defensive tool, one shared engine.

**Why last:** both are genuinely harder and only make sense once the core engine is trusted. v3 is where this becomes a *platform* story rather than a *tool* story — save it for when v1/v2 have already landed.

---

## What each version proves (for the résumé/LinkedIn narrative)

| Version | The sentence it earns |
|---------|----------------------|
| v1 | *"I built Chaos Monkey for data — it proves which corruptions your test suite lets through, safely, on clones."* |
| v2 | *"...and it validates your observability tools actually fire — a fire drill for Monte Carlo."* |
| v3 | *"...running continuously, and when something does break, it isolates whether it was code, data, or config."* |

Each sentence is complete on its own. Ship v1's sentence first.

---

## Anti-scope (what this roadmap deliberately excludes)
- **No product UI** (dashboards, settings, run-history web app, auth). The tool is a CLI; the only "UI" is the demo page.
- **No multi-tool support in v1** (dbt + one warehouse only).
- **No adoption/launch goals.** This is a portfolio artifact, not a company. Success = "impressive when explained," not stars.
- **No novelty-chasing.** The value is a working, shipped, hard-sounding tool executed with craft — not being first-to-market.

---

## The one rule that governs the whole roadmap
**Never confidently wrong.** The tool may say "config unavailable" or "pipeline non-deterministic — verdict unreliable," but it must never blame the wrong axis or falsely flag a silent fault (a fault counts as silent only if it passed tests *and* measurably changed the output vs a clean baseline). For a tool whose entire value is *trust*, a confident wrong answer is the only unforgivable failure.
