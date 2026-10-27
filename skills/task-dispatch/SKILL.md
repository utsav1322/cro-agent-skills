---
name: task-dispatch
description: Decide whether a task requires direct work, one specialised capability, or high-complexity planning and independent reviews.
argument-hint: "[task description]"
---

# Minimum Capability Task Dispatch

Requested task: $ARGUMENTS

## Objective

Choose the smallest sufficient execution path without loading or invoking unrelated capabilities.

## Do Not Use This Skill For

- `update md`, `update docs`, `save progress`, `update tasks` or progress recording.
- Simple project resolution handled by `project-start`.
- New capability review handled by `capability-intake`.

## Decision Process

1. Identify the exact requested outcome.
2. Identify the active project and affected work area.
3. Determine whether direct work is sufficient.
4. Assess task complexity internally from 0 to 100 using:
   - Number of modules affected.
   - Business-critical logic.
   - Authentication, permissions, finance, payments or sensitive-data impact.
   - External integrations.
   - Database or schema changes.
   - Production risk.
   - Unknowns, reversibility and regression risk.
5. If direct work is sufficient: use no extra skill, MCP, plugin or agent.
6. If specialised capability is required: read only the relevant section of `~/.claude/capability-registry.md`, read `~/.claude/agent.md` only when delegated review or execution is required, choose the smallest suitable capability, do not choose overlapping capabilities for the same purpose.
7. If complexity is below 80: proceed directly or with one required capability, perform relevant verification.
8. If complexity is 80+: state that work is high complexity, produce a short plan before major changes, use only necessary implementation capability, perform actual relevant verification, complete two independent review passes, resolve or report issues before declaring completion.

## Cross-Project Data Check

When a task references another project, clone, migration, white-label build, imported content, fetched data, shared module or database reuse:

1. Read `~/.claude/references/cross-project-data-copy.md`.
2. Treat the source project as reference-only by default.
3. Do not copy data or use another project's database without explicit approval.
4. Continue only with structure, logic or placeholder implementation where transfer is not approved.
5. Increase risk assessment when private data, databases, credentials or production records are involved.

## Release, Git Push and Deployment Check

When a task involves git push, release, merge, version tag, deployment, rollback or production movement:

1. Treat it as sensitive and require explicit instruction before write actions.
2. Read `<project>/docs/16-DEPLOYMENT.md` (+ its `.local.md`; unmigrated: `docs/deploy.md`) before proceeding.
3. Do not invent branch, release, version, tag, server or deployment details.
4. Use only required git or deployment capability after approval.
5. For a major release, require an approved version tag before pushing or releasing.
6. After actual release or deployment, add a release entry to `docs/17-CHANGELOG.md` and update `docs/01-PRD.md` §Scope status only where relevant (unmigrated: `docs/changelog.md`, `docs/completed-vs-scope.md`).

## Capability Restriction

- Do not inspect the complete skill, plugin, MCP or agent inventory.
- Do not invoke capability merely because it exists.
- Do not call several similar capabilities to compare results by default.
- Do not invoke deployment capability without explicit deployment instruction.
- Do not invoke gstack or external packs unless the current required workflow justifies it.

## Dispatch Output

Only when specialised capability or high-complexity process is required, report:

```
Execution path: <Specialised capability / High-complexity workflow>
Complexity: <score only for substantial work or when 80+ rule applies>
Capability selected: <capability name only when selected>
Reason: <one concise line>
```
