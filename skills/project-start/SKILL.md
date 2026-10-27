---
name: project-start
description: Start, resume or switch to a named project using minimum required context when the user says work on, resume, continue, open, switch to or check a project.
argument-hint: "[project-name] [optional task]"
---

# Start or Resume Project Work

Requested project or task: $ARGUMENTS

## Objective

Resolve the requested project and load only the documentation required to begin the current task.

## Process

1. Determine whether the current working directory is already the requested project.
   - If yes, do not read the global project index.
   - If no, read only the matching entry from `~/.claude/project-index.md`.
   - Use `~/.claude/context.md` only as fallback when the project cannot be resolved from the lightweight index.

2. Resolve only necessary information:
   - Project name.
   - Local project path.
   - Platform or short stack summary.
   - Environment, hosting or deployment information only when the task requires it.

3. Always read the project index: `<project>/CLAUDE.md`, or `<project>/.claude/CLAUDE.md` where the docs are local-only (git repo with a remote). If it has a `## Docs map` (v2 project), read only the mapped slots the task needs, plus the slot's `.local.md` where the map says `+local`:
   - resume / next work → `docs/08-IMPLEMENTATION.md` (+ `.local.md` §Checkpoint)
   - UI, layout, components → `02` · structure, refactor → `03` · schema → `04` · endpoints, webhooks → `05`
   - agent workflow, project skills → `06` · URLs, access, client → `07` · local setup → `09` · feature work → `10` (+ `01` for scope)
   - auth, permissions, security → `11` · MCP tooling → `12` · third-party services → `13` · tests, QA → `14`
   - bug, recurring issue → `15` · push, release, deploy, rollback → `16` · change history → `17`
   - Never go looking for a slot marked `unwritten`; create it from the code only when the task needs it (standard: `~/.claude/references/project-docs-standard.md`).

   If there is no Docs map (legacy project), read selectively and offer `setup-project-context migrate` once:
   - Read `<project>/rule.md` only when permanent unique project rules affect the task.
   - Read `<project>/docs/task.md` only when continuing current work or checking active implementation.
   - Read `<project>/docs/pending.md` only when selecting next work or reviewing blockers.
   - Read `<project>/docs/scope.md` only when validating whether work is included.
   - Read `<project>/docs/proposal.md` only when checking commercial commitments or original timelines.
   - Read `<project>/docs/completed-vs-scope.md` only for delivery status, handover or scope-completion checks.
   - Read `<project>/docs/changelog.md` only for confirmed change history or release reporting.
   - Read `<project>/docs/deploy.md` only for push, release, deployment, rollback, tagging or production work.
   - Read `<project>/context.md` only when prior technical state is required.
   - Read `<project>/DESIGN.md` only for UI, layout, component or responsive work.
   - Read `<project>/memory.md` only for recurring issues or known gotchas.
   - Read `<project>/spec.md` only for architecture, API, schema, authentication, permissions, calculations, security or core workflows.

4. Check `.claude/rules/` only for rules matching the affected work area.

5. Check `.claude/skills/` only when a unique project workflow is required.

## Capability Rule

- Project resolution does not require a specialist agent, MCP or plugin.
- Do not invoke implementation capabilities during project start unless the same request clearly requires specialised work.
- When capability selection is required after project resolution, use `task-dispatch`.

## Token Rules

- Do not read files only because they exist.
- Do not load unrelated project folders.
- Do not load full registry information when the requested project is already identified.
- Do not read `spec.md` for ordinary copy, styling or layout work.
- Do not read infrastructure or deployment files unless those actions are requested.

## Initial Response After Resolution

State only:

```
Project resolved: <project-name>
Docs: v2 | legacy
Context loaded: <files actually read>
Task focus: <requested task or next confirmed task>
```
