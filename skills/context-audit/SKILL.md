---
name: context-audit
description: Audit Claude Code configuration for oversized startup context, unnecessary imports, duplicated rules, duplicated workflows and incorrectly loaded capability information.
argument-hint: "[optional project path]"
---

# Audit Claude Code Context Usage

Target: $ARGUMENTS

## Objective

Identify unnecessary startup context and duplicated configuration while preserving useful instructions and safety rules.

## Restrictions

- Do not invoke agents, MCP servers, plugins, external packs or gstack.
- Do not bulk-read installed skill bodies.
- Do not modify application source code.
- Do not deploy, push, tag, release, merge or commit.

## Audit Checks

### Global Startup Context

- Count lines in `~/.claude/CLAUDE.md` (target: 35–55 lines).
- Identify imports loading large files at startup (any `@file` references).
- Identify capability inventories incorrectly stored in startup context.
- Identify workflow procedures that should live in skills.
- Confirm cross-project data rule and deployment approval rule remain concise.
- Confirm "read these files on every session start" instruction is absent.

### Project Startup Context

- Count lines in project `CLAUDE.md` files (target: ≤70 lines, no floor).
- Identify specifications, histories, scope records, proposal text, task logs, changelogs, deploy processes or duplicated global rules stored in startup files.
- Identify imported detailed documents (`@spec.md`, `@DESIGN.md`, etc.).

### Project Docs Standard (`~/.claude/references/project-docs-standard.md`)

- Fleet view: which projects are v2 (the index — `CLAUDE.md`, or `.claude/CLAUDE.md` in a repo with a remote — has `## Docs map`) and which are legacy.
- v2 projects (or run `python3 -I ~/.claude/skills/setup-project-context/scripts/docsmig.py audit <project>`):
  - Docs map rows match the files on disk and the project type (`unwritten` = absent, `+local` = `.local.md` present).
  - No empty / placeholder slots; no slot over 300 lines without a `docs/ref/` split.
  - No legacy files left beside a map (`rule.md`, `context.md`, `tasks.md`, `memory.md`, `agent.md`, root `DESIGN.md`, `docs/deploy.md`, `docs/changelog.md`…).
  - `*.local.md` ignored and untracked; repos with a remote track no project docs (`CLAUDE*.md`, `AGENTS*.md`, `docs/NN-*`, `docs/ref/`, `.claude/skills/`) — `docsmig.py audit` checks this.
  - No secret patterns in tracked docs; deploy excludes listed in `16-DEPLOYMENT.md` when the project root is uploaded.
  - Project skills that touch live systems set `disable-model-invocation: true`.
- Do not flag a missing slot that is marked `unwritten` or does not apply to the type.

### Rules

- Identify duplicated rules between global and project files.
- Identify path-specific rules suitable for `.claude/rules/`.
- Identify universal rules that must remain always available.

### Capabilities and Agents

- Identify custom workflows duplicating existing approved workflows.
- Identify project skills duplicating global custom skills.
- Identify capability registry entries that do not affect actual work.
- Confirm `agent.md` is on-demand only (not imported at session start).
- Confirm complexity 80+ requires two independent reviews.
- Confirm external cleanup inventory is not inside startup context.

### Data and Deployment Safety

- Confirm cross-project data policy reference exists in CLAUDE.md.
- Confirm deploy policy prevents push, tag, release or deployment without approval.
- Confirm major release tag rule exists.

## Required Output Format

```
Startup Context Issues:
- <file>: <issue>

Duplicate Content:
- <file or location>: <duplicate>

Documentation Split Issues:
- <project or file>: <issue>

Capability Routing Issues:
- <issue or None>

Safety Issues:
- <issue or None>

Recommended or Applied Changes:
- <change>

Validation:
- Global CLAUDE.md lines: <count>
- Project CLAUDE.md files above target (70 lines): <count>
- Projects on docs v2 / legacy: <count> / <count>
- Large startup imports found: <yes/no>
- Full capability inventory stored in startup context: <yes/no>
- Cross-project data rule present: <yes/no>
- Deployment approval rule present: <yes/no>
- Agent routing kept on demand: <yes/no>
- Application source modified: No
- Production actions performed: No

Git Summary:
- Modified configuration or Markdown files: <file paths>
- Commit created: No
- Push performed: No
```
