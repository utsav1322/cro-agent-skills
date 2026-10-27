---
name: update-md
description: Update project Markdown documentation from actual progress when the user says update md, update docs, save progress, update tasks, update context, update project md, record today's work or write progress.
argument-hint: "[optional project name or note]"
---

# Update Project Markdown from Actual Progress

Request details: $ARGUMENTS

## Purpose

Update only relevant project Markdown documentation using actual completed work, actual changed files and actual verification results.

## Activation Phrases

Use this workflow when the user says:
- update md / update docs / save progress / update tasks
- update context / update project md / record today's work
- write progress / update markdown / save current status

## Mandatory Restriction

For this request:
- Use `update-md` only.
- Do not use `task-dispatch`.
- Do not invoke agents, MCP servers, plugins, or unrelated skills.
- Do not perform new application work unless separately requested.
- Project docs stay on this machine: never stage, commit or push `CLAUDE.md`, `.claude/CLAUDE.md`, `AGENTS.md`, `AGENTS.local.md`, `docs/NN-*.md`, `docs/*.local.md`, `docs/ref/` or `.claude/skills/` in a repo with a remote (there the index is `.claude/CLAUDE.md`). If `git status` lists one, add the exclude block (`~/.claude/references/project-docs-standard.md` §7) to `.git/info/exclude` instead.

## Mandatory Inspection Before Writing

Before updating Markdown:

1. Identify the active project root.
2. Read the project index (`CLAUDE.md`, or `.claude/CLAUDE.md` in a repo with a remote) only if not already read in current context.
3. Inspect actual current progress using:
   - Work completed in the current session.
   - Files changed in the current session.
   - `git status --short`
   - `git diff --stat`
   - Relevant `git diff` output only where needed.
   - Build, lint, test, browser or manual verification actually performed.
4. Read only the documentation files needed for the update.

## File Selection Rules

### v2 projects (the index has `## Docs map`)

| Actual Situation | File to Update |
|---|---|
| Task added, started, blocked, waiting or phase changed | `docs/08-IMPLEMENTATION.md` |
| Session checkpoint (done · next · open decisions) | `docs/08-IMPLEMENTATION.local.md` §Checkpoint (overwrite, ≤10 lines) |
| Merged, shipped or released | `docs/17-CHANGELOG.md` (newest first) — and remove the item from 08 |
| Approved scope changed or deliverable status changed | `docs/01-PRD.md` §Scope / §Scope status |
| UI or design decision | `docs/02-DESIGN.md` |
| Structure or technical decision | `docs/03-ARCHITECTURE.md` (§Decisions: `- YYYY-MM-DD — decision — why`) |
| Schema or migration process | `docs/04-DATABASE.md` |
| Endpoint, server action or webhook | `docs/05-API.md` |
| How agents should work on this project, project skill added | `docs/06-AGENTS.md` |
| Client, URL, environment or access pointer | `docs/07-README.md` (sensitive → `.local.md`) |
| Setup steps or env var names | `docs/09-SETUP.md` |
| Feature specced, built or retired | `docs/10-FEATURES.md` |
| Auth, roles or security rule | `docs/11-AUTH-SECURITY.md` |
| MCP / AI tooling for this project | `docs/12-MCP.md` |
| Third-party service or tracking ID | `docs/13-INTEGRATIONS.md` |
| Test setup or QA checklist | `docs/14-TESTING-QA.md` |
| Reusable debugging lesson | `docs/15-DEBUGGING.md` (`### symptom` · Cause · Fix) |
| Deployment process or release policy | `docs/16-DEPLOYMENT.md` |
| Hard rule, stack, commands, or a slot created | the index — `CLAUDE.md` / `.claude/CLAUDE.md` (keep ≤70 lines; update the Docs map) |

- Slot marked `unwritten` and the work touched that area: create it now — facts from the code only, each section ending ``Source: `path` `` (standard: `~/.claude/references/project-docs-standard.md`). Remove the `unwritten` marker.
- Never recreate legacy files (`tasks.md`, `context.md`, `memory.md`, `rule.md`, `docs/deploy.md`…) in a v2 project.

### Legacy projects (no Docs map)

| Actual Situation | File to Update |
|---|---|
| Active task changed, completed or replaced | `docs/task.md` |
| New pending item, blocker or approval wait | `docs/pending.md` |
| Approved scope changed | `docs/scope.md` |
| Proposal or commercial commitment formally changed | `docs/proposal.md` |
| Approved deliverable completion status changed | `docs/completed-vs-scope.md` |
| Meaningful completed implementation change | `docs/changelog.md` |
| Deployment process or release policy changed | `docs/deploy.md` |
| Confirmed release, push, tag or deployment completed | `docs/changelog.md` |
| Meaningful technical implementation state changed | `context.md` |
| Reusable UI or design decision changed | `DESIGN.md` |
| Reusable debugging lesson found | `memory.md` |
| Architecture or specification-level rule changed | `spec.md` |
| Project operating instructions changed | the index (`CLAUDE.md` / `.claude/CLAUDE.md`) |
| Permanent unique project hard rule changed | `rule.md` |

## Never Do This

- Do not write assumed completion.
- Do not mark tasks complete without implementation evidence.
- Do not claim tests passed unless performed.
- Do not write planned testing as completed testing.
- Do not write long narrative progress summaries.
- Do not place ordinary progress inside `CLAUDE.md`, `rule.md` or `docs/06-AGENTS.md`.
- Do not update unrelated project documentation.
- Do not copy private cross-project data into Markdown.
- Do not record push, tag, release or deployment unless it actually happened.

## Required Progress Format

```md
## YYYY-MM-DD . <Short Task Name>

- Done: <Actual completed work. Maximum 2 lines.>
- Test: <Actual verification completed, or `Not tested yet`. Maximum 2 lines.>
- Next: <Pending step only when required. Maximum 2 lines.>
```

For several related completed items:

```md
## YYYY-MM-DD . Progress Update

- Done: <First actual completed item. Maximum 2 lines.>
- Done: <Second actual completed item. Maximum 2 lines.>
- Test: <Actual verification completed, or `Not tested yet`. Maximum 2 lines.>
- Next: <Pending step only when required. Maximum 2 lines.>
```

## Changelog Format

```md
## YYYY-MM-DD . <Short Change Title>

- Changed: <Confirmed completed change. Maximum 2 lines.>
- Test: <Actual verification performed, or `Not tested yet`. Maximum 2 lines.>
- Reference: <Scope item or affected feature only when useful. Maximum 1 line.>
```

## Release Changelog Format

```md
## YYYY-MM-DD . Release <version-or-short-title>

- Changed: <Confirmed released change. Maximum 2 lines.>
- Test: <Actual deployment or post-release verification. Maximum 2 lines.>
- Release: <Actual branch and tag only when used. Maximum 1 line.>
```

## Completion Response

Respond only with:

```
Updated:
- <file path>: <short description>

Recorded:
- Done: <one line>
- Test: <one line>
- Next: <one line only when applicable>

Git Summary:
- Modified documentation files: <file paths>
- Application source files modified: <None, unless separate user-requested implementation>
- Uncommitted changes detected: <yes/no based on actual git status>
```
