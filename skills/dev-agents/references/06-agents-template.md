# 06-AGENTS template (filled guide)

Writes `<project>/docs/06-AGENTS.md`. Headings match the canonical bare template at
`~/.claude/skills/setup-project-context/templates/06-AGENTS.md`. If they ever differ, that file wins.

Rules (project docs standard v2):
- Keep only headings with verified content. Create the file only if 3+ real lines remain. Never write TBD.
- Not here: hard rules (`CLAUDE.md` / `.claude/CLAUDE.md` Hard rules) or global rules (`~/.claude/rule.md`). Don't repeat them.
- Local-only: untracked, covered by `.git/info/exclude`. Never commit, push or PR it.
- Words, not emoji. Dates `YYYY-MM-DD`. No secret values, pointers only. Cap 300 lines.
- Update when how Claude / Codex should work on this project changes (via `update-md`).

---

```markdown
# Agents

## Autonomy

Do without asking:
- <e.g. edit app code on a feature branch, run typecheck / lint / tests locally>
- <e.g. run migrations against the local dev DB only>

Ask first:
- <e.g. push + open PR (account `<account>`, via GH_TOKEN prefix)>
- <e.g. any change under prisma/migrations or the payments module>
- <e.g. deploy: <window / who approves>, see 16-DEPLOYMENT>

Standing approvals (override the global ask-first default; date each):
- <YYYY-MM-DD — e.g. "PR → merge → deploy without asking" (Hub pattern)>

## Workflows

- Code changes: `build-review-loop`. Multi-part features: `dev-agents`.
- Parallel builds: <worktrees yes/no> · max builders <n> · contract files owned by main thread: <paths>.
- Full build: <run locally | run on the VPS only (local OOM)>. Command: see 14-TESTING-QA.
- Branch names: `feat/…`, `fix/…`. PR base: <main | dev>.
- <project-specific flow, e.g. "Shopify: pull live theme first, push to unpublished, `theme list` after">

## Review

- Panel: Claude + Codex <on | Codex off: reason, e.g. client NDA on source>.
- Pass 2 focus (complexity 80+ or when touched): <security | finance calc | data integrity | perf>.
- P1 here also means: <e.g. any query without tenant filter, any money math in floats, any page missing requireSession()>.
- Verify end state with: <e.g. chrome-devtools on staging URL, a real order on test gateway, DB row check>.

## Soft rules

- <naming / folder conventions not enforced by lint>
- <UI layer: Astryx + Motion (React/Next only) | none for WP/Liquid/PHP>
- <copy, tone, client-brand prefix `<brand>-`>

## Project skills

| Skill | Path | Use when |
|---|---|---|
| <name> | `.claude/skills/<name>/SKILL.md` | <trigger> |
```
