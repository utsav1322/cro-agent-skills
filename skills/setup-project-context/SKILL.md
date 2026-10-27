---
name: setup-project-context
description: Create, migrate or audit a project's docs to the numbered docs/01–17 standard (lean CLAUDE.md index + slots). Use for new projects, for restructuring legacy docs (rule.md, context.md, tasks.md, memory.md, DESIGN.md, docs/deploy.md…), or for checking compliance.
argument-hint: "new|migrate|audit <project-path-or-name> [type]"
---

# Project Docs — new / migrate / audit

Request: $ARGUMENTS

- Standard (read first): `~/.claude/references/project-docs-standard.md`
- Templates (guides, never copied empty): `~/.claude/skills/setup-project-context/templates/`
- Engine: `python3 -I ~/.claude/skills/setup-project-context/scripts/docsmig.py --help`
- Run dir (snapshots, staging, reports): `$DOCSMIG_RUN`, default `~/Desktop/<workspace>/_backups/docs-migration-<date>/` (chmod 700)

## Restrictions

- Do not invoke agents, MCP servers, plugins, external packs or gstack inside this skill. A batch orchestrator may run one subagent per project; that subagent follows these restrictions.
- Do not modify application source code or committed ignore files. Local ignore rules go in `.git/info/exclude`.
- Never push, merge, tag, release, open PRs or deploy. Project docs never leave this machine (standard §7): a git repo with a remote ends `migrate` with `docsmig.py localize` (one local commit `docs: stop tracking internal project docs`, docs ignored); `docsmig.py commit` (branch `docs-restructure`) is only for git repos without a remote. No AI attribution anywhere.
- `docsmig.py localize` and `docsmig.py adopt` change the user's checkout — run them only after the user approves migrating that project.
- No secret values anywhere — vault pointers only. Never open `vault*`, `*secret*`, `*credential*`, `.env*` (only `.env.example` / `.env.sample` may be read, for variable names).
- Never copy global rules or global memory notes into project files. Never create empty or placeholder files.

## Mode: new

1. Resolve the project path and type (standard §4). Read the brief or proposal if one is provided.
2. Write `CLAUDE.md` from `templates/CLAUDE.md` (≤70 lines). Docs map = applicable slots; every missing file marked `unwritten`.
3. Create only slots that have real content now (usually 01, 07, 08; plus 03/09 once a scaffold exists). Strip all template comments.
4. Git repo: append the exclude block (standard §7) to `.git/info/exclude` before writing any doc, then confirm `git status` shows none of them. With a remote, write the index as `.claude/CLAUDE.md`, not `CLAUDE.md`. If `CLAUDE.md` or other docs are already tracked, untrack them only after user OK, in one commit `docs: stop tracking internal project docs`.
5. Report (format below).

## Mode: migrate

1. `docsmig.py prepare <project>` → snapshot + `plan.json` (mode, base sha, private paths, allowed slots, active flag, out dir). Exit 30 = MANUAL: stop and report.
2. Read only the snapshot files listed in `plan.json`; read the live tree only for backfill.
3. Build the new docs under the `out/` dir from `plan.json` (it mirrors project paths):
   - Route whole sections verbatim with the legacy map (standard §9). Keep wording; only adjust heading levels.
   - Material over 300 lines → `out/docs/ref/` byte-identical, linked from its slot.
   - Content from private (ignored) sources → only `docs/NN-<SLOT>.local.md`.
   - Exact duplicates and copies of global rules → drop, and log each in `ledger.tsv` as `<line>\t<reason>`; reasons: `dup-of:<file>:<line>`, `global-dup:<file>:<line>`, `legacy-pointer`, `secret`.
   - Root `SKILL.md` → `.claude/skills/<name>/SKILL.md` with frontmatter (`name`, `description`; `disable-model-invocation: true` when it touches live systems).
   - **Active projects only — backfill** missing applicable slots from code (standard §3), reading ≤25 files; every backfilled section ends with ``Source: `path` ``. Never write 01, 07, 08, 15 or 17 from code; never infer intent, status, hosts or values.
   - `CLAUDE.md` from the template: identity line, Hard rules (damage-if-violated only), Stack, Commands (must exist), Docs map matching `out/` (`unwritten`, `+local`).
4. `docsmig.py verify <project>` → fix and re-run, at most 2 retries. Still failing = FAIL, report.
5. Git repo with a remote: `docsmig.py localize <project> --check`, then (after user OK) `docsmig.py localize <project>`. Several worktrees of one repo: `docsmig.py materialize <source-worktree> <shared-folder>` (outside every repo), then `localize <each worktree> --link-from <shared-folder>`. Git repo without a remote: `docsmig.py commit <project>`. In-place mode: `docsmig.py apply <project>`.
6. Write `report.md` in the project's run folder: moved, split, dropped (ledger count + reasons), backfilled slots, warnings.
7. Return one line: `STATUS <slug> <mode> <localized@sha|branch@sha|applied> slots=<n> local=<n> ref=<n> backfill=<slots> ledger=<n> warn=<n> "<note>"`.

## Mode: audit

Read-only: `docsmig.py audit <project>`. Checks Docs map vs disk vs type, no placeholder slots, no legacy files beside a map, `.local.md` ignored and untracked, docs untracked and ignored in repos with a remote, CLAUDE.md ≤70 lines, no secret patterns in tracked docs, deploy excludes listed in 16 when the project root is uploaded.

## Result reporting

```
Mode: <new|migrate|audit> · Project: <path> · Type: <type> · Docs: v2|legacy
Created/Updated: <paths>
Moved: <legacy file → slot>, …
Dropped (ledger): <n> lines (<reasons>)
Backfilled: <slots> (sources cited)
Git: localized @<sha> | docs-restructure @<sha> (no remote) | in-place (snapshot <path>) | none
Push performed: No
```
