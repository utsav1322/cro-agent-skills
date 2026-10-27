---
name: build-review-loop
description: Default build-and-review loop for any real coding request typed in the composer — writing, editing, refactoring or fixing application code, components, endpoints, scripts, migrations or config with logic. Runs plan → build → parallel review panel (Claude + Codex) → merged issue table → fix all P1s → re-review → summary. Auto-invoke on any non-trivial code change. SKIP for trivial one-liners, comments, docs, config typos, or when the user says "skip review".
argument-hint: "[optional task note]"
---

# Default Build & Review Loop

Task: $ARGUMENTS

Encodes the standing loop from the global and project `CLAUDE.md`. Run it automatically for any real coding request — no slash command needed. Stay in caveman mode throughout so output stays cheap (caveman already relaxes for the plan/summary and safety-critical text).

## When to run

Run this loop for any request that writes or changes code with logic: features, edits, refactors, bug fixes, endpoints, components, scripts, migrations, non-trivial config.

**Skip the loop** (do the edit directly) for:
- Trivial one-liners
- Comments or docs
- Config typos
- The user explicitly says "skip review"

## The loop

### 1. Plan
Reply with a **4–5 line** summary/plan of the approach, then proceed. No essay — just the shape of the change and the files touched.

### 2. Build
Write the code. Follow project conventions, the active project's `CLAUDE.md`, and the locked rules (PR-only, no AI attribution, keep sensitive data local, respect deploy windows).

### 3. Review panel (parallel)
Get independent reviews of the diff. **Active reviewers: Claude + Codex.**
- **Claude** — run `/review` (or a focused self-review of the diff).
- **Codex** — run `/codex review`.
- **Kimi / DeepSeek** — ⏸️ ON HOLD (no account balance). Do NOT call them until re-enabled in `~/.claude/CLAUDE.md`.
- Any active reviewer that exits non-zero / is unauthed → mark **skipped** and continue. **Never block on one reviewer.**
- Log each active reviewer's result as a JSON line:
  `gstack-review-log '{"skill":"build-review-loop","status":"...","findings":...}'`
  (reuses the existing `<branch>-reviews.jsonl`.)

### 4. Issue table
Merge all findings into one table, dedup overlaps, note where reviewers agree:

| # | Severity | Source(s) | File:Line | Issue | Suggested fix |
|---|----------|-----------|-----------|-------|---------------|

### 5. Fix
Rewrite the code to resolve **every `P1`**.

### 6. Re-review
Repeat steps 3–5 until no `P1` remains. **Max 3 rounds.** If a `P1` survives after 3 rounds, report it honestly instead of looping forever.

### 7. Summary
Close with a **4–5 line** wrap-up: what changed, what each model flagged, what's left.

## Reviewer keys / verification
- Kimi → `~/.config/moonshot/key` (or `MOONSHOT_API_KEY`)
- DeepSeek → `~/.config/deepseek/key` (or `DEEPSEEK_API_KEY`)
- Verify a provider is reachable: `bash ~/.claude/review-panel/panel-review.sh <provider> --check` (expect `http=200`).
- To re-enable Kimi/DeepSeek: recharge the account, confirm the `--check` returns `http=200`, then add them back as active reviewers in `~/.claude/CLAUDE.md` and here in step 3.
