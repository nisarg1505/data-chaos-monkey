# SETUP.md

Setup guide for **Data Chaos Monkey** on **macOS** (Apple Silicon — M1/M2/M3/M4).

This is a **decision tree**, not a script. For each tool: run the **check**, then follow the branch that matches what you see. If a check passes, skip to the next tool. No assumptions about what's already on your machine.

Target versions: **Python ≥ 3.11**, plus Homebrew, Git, uv, an editor.

> Tip: paste each **check** command, read the output, then jump to the matching **→ branch**. Every section ends with a **✅ done-when**.

---

## 1 · Homebrew (the Mac package manager)

**Check:**
```bash
brew --version
```

**→ If you see a version** (e.g. `Homebrew 4.x`) → ✅ skip to §2.

**→ If you see `command not found`** → install it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Then add it to your PATH (Apple Silicon path shown; the installer also prints these — use whatever it prints):
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

**→ If `brew` is installed but `command not found` in a new terminal** → the PATH line is missing; re-run the two lines above.

**✅ done-when:** `brew --version` prints a version in a **new** terminal window.

---

## 2 · Git

**Check:**
```bash
git --version
```

**→ If you see `git version 2.30`+** → ✅ configure identity (below), then §3.

**→ If missing, or version < 2.30** → install/upgrade:
```bash
brew install git
```
> macOS sometimes ships an old Apple Git. If `git --version` still shows an old one after `brew install`, your PATH is finding the system git first. Fix:
> ```bash
> echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zprofile && source ~/.zprofile
> ```
> Then re-check `git --version`.

**Configure identity** (once, used on all commits):
```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

**✅ done-when:** `git --version` ≥ 2.30 and `git config --global user.name` prints your name.

---

## 3 · Python ≥ 3.11  (the common gotcha)

macOS ships an old system Python. **You do NOT need to touch the system Python** — we let `uv` (next step) manage a clean, project-local Python. But first, see what you have so the branch is clear.

**Check:**
```bash
python3 --version
```

**→ If you see `Python 3.11`, `3.12`, or `3.13`** → good, but we'll *still* use uv's managed Python for isolation. Skip to §4.

**→ If you see `Python 3.9.x` / `3.10.x` (too old)** → **do not upgrade system Python by hand.** This is the exact case `uv` solves — it installs the right Python *inside the project*, leaving your system untouched. Just continue to §4; uv handles it in §4's `uv python install`.

**→ If you see `command not found`** → also fine; uv installs Python in §4.

> **Why we don't `brew install python@3.12` and call it a day:** mixing brew-Python, system-Python, and pyenv is the #1 source of "works on my machine" pain. `uv` pins one project-local interpreter and version, so the repo is reproducible for anyone. That's the approach this repo standardizes on.

**✅ done-when:** you've noted your current `python3` version and understood you don't need to fix it manually — uv will.

---

## 4 · uv (Python + dependency manager — the core tool)

**Check:**
```bash
uv --version
```

**→ If you see a version** → skip to "install project Python" below.

**→ If `command not found`** → install:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Reload your shell (or open a new terminal):
```bash
source ~/.zprofile 2>/dev/null; source ~/.zshrc 2>/dev/null; true
```

**→ If still `command not found` after install** → close Terminal completely, open a new window, re-check.

**Install the project's Python** (this is what fixes any wrong-version issue from §3):
```bash
uv python install 3.12
```

**✅ done-when:** `uv --version` prints, and `uv python list` shows 3.12 installed.

---

## 5 · Editor

**Check:** do you already have VS Code or Cursor?
```bash
code --version 2>/dev/null || cursor --version 2>/dev/null || echo "no editor CLI found"
```

**→ If you have one** → ✅ skip to §6.

**→ If none** → install one:
```bash
# VS Code (safe default):
brew install --cask visual-studio-code
# OR Cursor (AI-native, VS Code fork — everything here works identically, use `cursor .`):
brew install --cask cursor
```

**Optional — nicer Markdown reading** (so docs don't look like raw syntax):
```bash
brew install --cask typora     # $15, calmest reader
# or: brew install --cask obsidian   # free
```
*(Or skip both — VS Code/Cursor preview Markdown with **Cmd+Shift+V**.)*

**✅ done-when:** `code .` (or `cursor .`) opens a folder.

---

## 6 · Clone / create the project

**If the repo already exists on GitHub:**
```bash
git clone <repo-url> data-chaos-monkey
cd data-chaos-monkey
```

**If you're starting it fresh:**
```bash
mkdir -p ~/projects/data-chaos-monkey && cd ~/projects/data-chaos-monkey
git init
uv init --package --name chaos_monkey --python 3.12
```

**✅ done-when:** you're inside the project dir and `ls` shows `pyproject.toml`.

---

## 7 · Install dependencies

```bash
# core runtime
uv add dbt-core dbt-duckdb sqlglot pandas duckdb click rich
# dev tooling
uv add --dev pytest ruff pre-commit
```
> Snowflake deps are **not** installed now — they come only at the demo stage:
> `uv add dbt-snowflake snowflake-connector-python`

**Check it worked:**
```bash
uv run python -c "import dbt, duckdb, sqlglot, click, rich; print('all imports OK')"
```

**→ If you see `all imports OK`** → ✅ §8.
**→ If an import fails** → run `uv sync` and re-check; if a single package fails, `uv add <package>` again.

**✅ done-when:** the import line prints `all imports OK`.

---

## 8 · Hooks + first commit

```bash
uv run pre-commit install
git add -A
git commit -m "chore: project setup"
```

**✅ done-when:** `git log --oneline` shows your commit.

---

## Final verification — you're ready to build

Run all four; each should succeed:
```bash
brew --version          # §1
git --version           # §2  (≥ 2.30)
uv --version            # §4
uv run python -c "import dbt, duckdb, sqlglot; print('env OK')"   # §7
```

If all four pass, setup is complete. **Next step: build the M0 fixture** (see the execution doc) — a small, deliberately-breakable dbt project plus a written list of which columns are guarded vs unguarded.

---

## Troubleshooting (quick reference)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `command not found` right after installing something | PATH not reloaded | Close Terminal, open a new window |
| `brew: command not found` on Apple Silicon | Missing PATH line | Re-run the two `brew shellenv` lines from §1 |
| `git --version` shows an old Apple version after `brew install git` | System git found first | `export PATH="/opt/homebrew/bin:$PATH"` in `~/.zprofile`, then `source` it |
| `python3` is 3.9 and I'm worried | Nothing to worry about | We don't use system Python; uv pins 3.12 (§4). Leave system Python alone |
| `uv` not found after install | Shell not reloaded | `source ~/.zprofile` or open a new terminal |
| `uv run` import errors | Env out of sync | `uv sync`, then retry |
| `make: missing separator` | Makefile has spaces not tabs | Regenerate it with the `printf` command (don't hand-edit tabs) |

---

## Version reference

| Tool | Minimum | This repo pins |
|------|---------|----------------|
| macOS | Apple Silicon (M-series) | — |
| Python | 3.11 | **3.12** (via uv) |
| Git | 2.30 | latest (brew) |
| uv | any recent | latest |
| dbt-core | 1.7 | latest compatible |

*All Python dependencies are locked in `uv.lock` — anyone who clones and runs `uv sync` gets the exact same environment.*
