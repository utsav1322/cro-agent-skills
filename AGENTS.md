# AGENTS.md

Guide for any coding agent (Claude Code, Codex, Cursor, or other) working with this repo.

## What this repo is

A library of **Claude Code skills** under [`skills/`](skills/). Each skill is a folder with a `SKILL.md` (YAML frontmatter `name` + `description`, then Markdown instructions) and optional `references/`, `scripts/`, and `templates/`. There is no build step and no hosted service.

## How to use the skills

- **Claude Code / Claude apps** — native. Copy a skill folder into `~/.claude/skills/` and it is auto-discovered and model-invoked when a request matches its `description`. No slash command needed.
- **Any other agent (Codex, Cursor, …)** — skills do not auto-fire, so use them as content: open the relevant `skills/<name>/SKILL.md`, follow its instructions, pull in its `references/` when the body points to them, and run its `scripts/` as documented. You can also paste a `SKILL.md` straight into a model.

## Working in this repo

- **Keep it generic and clean.** No secrets, no personal or client data, no internal-only paths. A leak gate (`scripts/scrub_gate.py gate <dir>`) runs before anything is published and fails on brand/email/path/private references.
- **Validate** skill metadata with `python3 scripts/validate-skills.py` (valid frontmatter, name matches folder, non-empty body).
- **Regenerate the README tables** with `python3 scripts/build-readme.py` after adding or editing a skill.
- **Third-party sources** are listed in `third-party-sources.json` (not vendored); `scripts/update-third-party.sh --check` reports upstream drift.
- Changes land via pull request to `main`.

## Pointers

- [README.md](README.md) — install, the full skill index, portability, and the good-repos library.
- [GOOD-REPOS.md](GOOD-REPOS.md) — tracked skill/tool repos with verdicts and a monthly review.
- [SECURITY.md](SECURITY.md) — how to report a security or leaked-data issue.
