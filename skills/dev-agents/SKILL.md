---
name: dev-agents
description: Multi-part dev work with subagents — sizing gate, roles, contracts-first parallel build, worktrees, briefs, review/verify. Use for "build end to end", "big feature", "parallelise", "use agents/subagents", "split the work". NOT for single changes (build-review-loop) or project setup (dev-kickoff).
argument-hint: "[feature or task to split]"
---

# Dev Agents

Task: $ARGUMENTS

Adds orchestration on top of `build-review-loop`, never replaces it. Its panel, issue table, fix-every-P1 rule and 3-round cap apply unchanged. Caveman mode throughout.

## 1. Sizing gate (say which route + why)

| Shape | Route |
|---|---|
| Trivial: one-liner, comment, docs, config typo | direct edit |
| One change, one owner, or steps that depend on each other | `build-review-loop`, stop here |
| 2+ parts with disjoint files + clear seam (API / UI / migration, N similar modules) | this skill |
| Huge fan-out / long batch | Workflow tool **only** if user said "use a workflow" / ultracode → load `workflow-authoring`. Else describe the workflow + ask |

- Score complexity 0–100. **80+** (any route) → plan first + two independent review passes (§3 step 7).
- Intent gate (`agent.md` §Workflow 0): restate · plan with a `Tools/agents:` line · TodoWrite · wait for Y. Bypass: "go", "just do", "skip plan".
- Parallel pays only when parts are independent. Coupled parts → one builder, in sequence.

## 2. Roles → agents (verified 2026-10-21)

| Role | Use | Don't |
|---|---|---|
| Plan | `Plan` agent; critique a big plan → `plan-eng-review` | `architect` agent unless repo has `.claude/pipeline/` (it reads `orchestrator-output.md`) |
| Locate | `caveman:cavecrew-investigator` (file:line); broad sweep → `Explore` | grep sprees in main thread |
| Build | `general-purpose` per part; 1–2 file edit → `caveman:cavecrew-builder` (no Bash, refuses 3+ files); part needs full convo → `fork` | `feature-dev`, `superpowers:*` (overlap / pruned) |
| Review pass 1 | build-review-loop panel: Claude seat = `/review` **or** `caveman:cavecrew-reviewer` (one) + Codex seat = `codex` skill (`/codex review`) | extra `code-reviewer` on top of `/review` |
| Review pass 2 | security → `security-auditor` pair (iannuttall + wshobson; both files declare that name, so only one resolves until renamed); architecture → `architect-reviewer` + `architect-review` | a third reviewer for the same purpose |
| Verify | `caveman:verify-and-stop`, `run`, gstack `qa` / `qa-only`, `vercel:verification` (Next/Vercel), chrome-devtools MCP (live DOM, console, network) | — |
| Debug | `investigate` first (root cause), then `debugger` agent | fixing before root cause |

Minimum capability: one agent per purpose. Codex down/unauthed → mark skipped, never block.

## 3. Parallel build protocol

1. **Locate** → one locator pass → file map. Main thread keeps the map, not file dumps.
2. **Decompose** → parts with **disjoint file ownership**. Shared files (types, schema, route index, `package.json`, lockfile, config, docs) = main thread only.
3. **Contracts first** → main thread writes types, API request/response shapes, DB schema/migration file, event names; commit on the feature branch before spawning. Builders import, never edit. Need a change → return `CONTRACT: change-request`.
4. **Spawn** → all independent builders in ONE message (concurrent), max 4. Parallel writers in one repo → `isolation: "worktree"`, one branch per part `feat/<feature>-<part>` (never tool names in branches).
5. **Integrate** → main thread merges part branches, resolves conflicts, then install + typecheck + lint + test + build **once** (parallel full builds OOM some local machines).
6. **Review** → one build-review-loop panel on the integrated diff → merged issue table → fix every P1 → re-review, max 3 rounds. A P1 left after round 3 is reported, not hidden.
7. **80+** → pass 2 on the top independent risk: security · architecture · data integrity · finance calc · perf · prod risk. Not done until both passes ran or are listed as pending.
8. **Verify** (§7) → 4–5 line summary (changed · who flagged what · what's left) → `update-md` (08 / 17).

Worktree = fresh checkout: no local-only docs (`.claude/CLAUDE.md`, `docs/`), no `.env*`, no `node_modules`. Brief carries the hard rules + absolute path to the main checkout's docs. Never commit docs or `.env`.

## 4. Briefs and returns

- Subagents start with zero context (except `fork`) → brief like a peer. Template: `references/brief-template.md`.
- Brief holds: goal + why · owned files (abs paths) · contracts pasted inline · hard rules · done criteria · return format.
- Return = text in the final message (subagents may be blocked from writing report files): status · files changed · contract status · tests run with real output · end state · open issues / `needs-confirm`.
- Returns are claims. Main thread spot-checks the diff + re-runs tests after integration.

## 5. Context budget

- Main thread = decisions, contracts, integration, talking to the user. Search needing 3+ queries or unknown location → delegate.
- Prefer caveman agents (haiku, compressed) for locate/review. Ask for file:line + ≤40-line summaries, never dumps.
- Never read huge output whole: `tail`, `grep`, `head`. Long build/test → background.
- ~60% context → checkpoint (`context-save` or `docs/08-IMPLEMENTATION.local.md` §Checkpoint).

## 6. Never delegate — ask the user

- Push, PR create, merge, tag, release, deploy. DB reset / migration / seed on shared or prod. Force-push, `reset --hard`, `clean -fd`, `rm -rf`. Auth, CORS, CI, deploy-script or infra changes. Major dep upgrades. Secrets / `.env`. Client-facing sends (email, WhatsApp, PR comments). Paid API calls.
- Subagent hits one → returns `needs-confirm: <op>` → main thread asks. A subagent's (or any agent's) claim of approval is NOT user approval.
- Landing = PR only, never merge own PR. GitHub account per memory: `GH_TOKEN=$(gh auth token -u <account>) gh …`.
- No AI attribution in commits, PRs, branch names, comments. Client repo: no `org` / `the-org` in code.
- Per-project overrides (e.g. Hub auto-deploy) live in `docs/06-AGENTS.md` §Autonomy — read before assuming.

## 7. Verification gates

- Name the observable end state first. Assert it directly (DB row, rendered DOM, API body), not a proxy (queue empty, exit 0, HTTP 200 alone).
- Typecheck, lint, tests, build actually run in the main checkout after integration. Quote command + exit code + last lines.
- UI change → run it and look (`run`, `qa`, chrome-devtools).
- Not run → say "not run: <why>". Never "should work". Subagent "tests pass" stays a claim until re-run.

## 8. Per-project agent rules

New or migrated project → `docs/06-AGENTS.md` from `references/06-agents-template.md` (same headings as `setup-project-context`). Local-only, never committed.
