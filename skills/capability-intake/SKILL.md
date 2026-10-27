---
name: capability-intake
description: Study one newly installed skill, MCP server, plugin, agent pack, hook, integration or tool and document only behaviour required for actual workflows.
argument-hint: "[new capability name, type and optional scope]"
---

# Capability Intake

New capability: $ARGUMENTS

## Objective

Study one newly added capability and update only the minimum required documentation when it changes actual workflow, routing, safety or a confirmed project dependency.

## Activation Examples

Use this workflow when the user says:
- `I installed <capability>. Check it.`
- `Add this MCP if required.`
- `Study this plugin and update the setup if useful.`
- `I added a new skill. Keep it only where required.`
- `Check this new agent pack.`

## Restrictions

- Study one new capability at a time.
- Do not automatically register every installation.
- Do not bulk-read other capabilities.
- Do not invoke a capability simply to inspect it when its own configuration or documentation is sufficient.
- Do not modify startup context unless a new permanent universal rule is required.
- Do not update agent routing unless the capability materially changes delegation policy.
- Do not add project notes unless a capability is actually required by that project.
- Do not duplicate automatic hook behaviour.
- Do not deploy, push, tag, release, merge or commit.

## Intake Process

1. Identify capability type: Skill / MCP server / Plugin / Agent or agent pack / Hook / Integration / Other tool.

2. Identify capability scope: Global or user-level / Project-specific / Development-only / Fallback-only / Production-sensitive.

3. Read only minimum source required to understand that single capability: its own manifest, config, SKILL.md, README, or directly relevant routing file.

4. Determine:
   - Exact outcome supported.
   - Whether it duplicates an approved workflow.
   - Whether it should remain installed but undocumented.
   - Whether it is useful on demand.
   - Whether it creates a new safety or production risk.
   - Whether it changes task dispatch or agent policy.
   - Whether it is essential for one project.
   - Whether it can access data, databases, private files, analytics, credentials or external systems.
   - Whether no documentation change is required.

## Data Access Capability Check

When the capability can access databases, project files, client data, analytics records, credentials or external systems:
- Determine whether it can read or modify cross-project data.
- Record a safety note only when it changes real access risk or workflow.
- Do not approve automatic cross-project use.
- Do not add a project dependency unless the project genuinely requires it.

## Allowed Decisions

### Ignore for Documentation
Capability is installed but does not affect an approved workflow, routing or safety rule.
Action: update nothing.

### Add as Approved On-Demand Capability
Capability is useful for a defined real global workflow but not every session.
Action: add one concise entry to `~/.claude/capability-registry.md`. Do not update global CLAUDE.md.

### Add as Project-Specific Dependency
Capability is required only for one project.
Action: add a concise note to `<project>/docs/12-MCP.md` (MCP/AI tooling), `docs/13-INTEGRATIONS.md` (third-party service) or `docs/06-AGENTS.md` (agent/workflow) — unmigrated: `context.md`. Add a line to `<project>/CLAUDE.md` only when essential in routine project work.

### Update Agent Policy
An agent or delegated capability materially changes actual routing.
Action: add only required policy or routing note to `~/.claude/agent.md`. Do not copy full pack documentation.

### Update Universal Rule
A permanent rule applies nearly every session.
Action: add one concise rule to `~/.claude/CLAUDE.md` (use rarely).

### Update Safety or Hook Reference
A new capability changes automatic safety, lifecycle or destructive-action behaviour.
Action: record only the required operational note. Do not duplicate automatic behaviour.

## Required Response Format

```
Capability Reviewed
- Name: <capability name>
- Type: <skill / MCP / plugin / agent / hook / integration / tool>
- Scope: <global / project-specific / fallback / production-sensitive>
- Purpose: <one concise line>

Decision
- <Ignore for documentation / Add as on-demand capability / Add to project context / Update agent policy / Update universal rule / Update safety reference>

Reason
- <short factual bullet>

Files Updated
- <file path>: <minimal change made>

Git Summary
- Modified configuration or Markdown files: <file paths or None>
- Application source files modified: None
- Commit created: No
- Push performed: No
```
