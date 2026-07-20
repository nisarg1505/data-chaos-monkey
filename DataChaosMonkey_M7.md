# M7 — The Money-Shot Demo (capture guide)

> Not a coding milestone — a *capture* one. The engine works (M0–M6). M7 records the reveal so you have a postable artifact: a green test suite, then your tool exposing the hidden SILENT hole. This is the thing that goes in the README and (later) the LinkedIn post.

**Where you are:** M0–M6 done. `chaos-monkey report` works.

**Goal:** a ~20–40 second recording (GIF or video) that makes a viewer *feel* "green tests, but corrupted data got through."

---

## The narrative arc (this is what makes it land)

The reveal only works if you show the *false confidence first*, then break it:

```
1. "Here's my pipeline. All tests pass." → show dbt test, all green ✅
2. "Looks healthy, right?"               → (the false confidence)
3. "Now watch."                          → run chaos-monkey report
4. "3 of 4 faults caught — but ONE       → the SILENT row, red
    reaches the dashboard silently."
5. "status enum-drift → revenue          → the concrete damage
    dropped $150, no test noticed."
```

The emotional payload is the gap between step 2 (looks fine) and step 4 (it wasn't). Don't skip step 1 — the green suite *is* the setup.

---

## Step 1 · Make the demo reproducible

Add a `make demo` target so the recording is one clean command. In your `Makefile`:

```makefile
demo:
	@echo "=== 1. The pipeline's tests all pass ==="
	cd fixture/dbt_project && uv run dbt test --profiles-dir . && cd ..
	@echo ""
	@echo "=== 2. But Chaos Monkey finds what they miss ==="
	uv run chaos-monkey report
```

Test it:
```bash
make demo
```
You want: green dbt tests, then the resilience report with the SILENT row. Clean, top to bottom, one command.

---

## Step 2 · Record it

**Option A — Terminal GIF (recommended, lightweight).**
Use `asciinema` + `agg`, or the simplest path: a screen-recording tool cropped to the terminal.

Quickest on Mac:
```bash
brew install asciinema
brew install agg        # converts asciinema recording to GIF
```
Record:
```bash
asciinema rec demo.cast
# (inside the recording session:)
make demo
# then type: exit
```
Convert to GIF:
```bash
agg demo.cast demo.gif
```

**Option B — Screen recording (simplest, no installs).**
`Cmd+Shift+5` on Mac → record a selected portion → run `make demo` → stop. Trim in QuickTime. Export as `.mov` or convert to GIF later.

Either works. GIF is best for a README (auto-plays, no click). Keep it under ~40 seconds.

---

## Step 3 · Make the reveal visually sharp

A few touches that make it pop (optional but worth it):
- **Widen the terminal** so the report table doesn't wrap.
- **Increase font size** (readable in a small embedded GIF).
- **Pause ~1 second** after the green tests before running the report — let the "all passing" register before you break it.
- Consider a dark theme — the red SILENT row pops against dark.

---

## Step 4 · Drop it in the README

Put the GIF at the very top of `README.md`, above everything — same move as Headroom's token-count GIF. First thing a visitor sees:

```markdown
# Data Chaos Monkey

> Chaos engineering for your data, not your infrastructure.
> Your tests pass. Your data is still broken. This proves it.

![demo](demo.gif)

Everyone builds the fire alarm (observability). This is the fire drill —
it proves which corruptions your test suite lets through, safely, on clones.
```

Commit the GIF:
```bash
git add demo.gif README.md
git commit -m "M7 demo GIF + README"
git push
```
(Note: `.gif` isn't in your `.gitignore`, so it'll commit fine. If it's large >5MB, consider compressing.)

---

## ✅ Done when
- [ ] `make demo` runs the full reveal in one command
- [ ] A GIF/recording captures: green tests → report → SILENT row
- [ ] GIF is at the top of README with the fire-drill framing
- [ ] committed + pushed

---

## What NOT to do yet
- **Don't post to LinkedIn yet.** M7 gives you the artifact; M8 (the live interactive page) is the stronger launch surface. Post after M8 with a link people can *try*, not just watch.
- **Don't over-produce the video.** A clean terminal GIF beats a polished but slow screencast. The content is the reveal, not the production.

---

## Next: M8 (ship + live demo page = "the website")
M7 is a recording; M8 is a hosted page where a stranger clicks "inject a fault" and watches the verdict live in-browser. That's the top-of-resume URL and the real LinkedIn launch. After M8, you post.
