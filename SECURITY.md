# Security Policy

This repository ships **Claude Code skills** — Markdown instructions plus small helper scripts (`scripts/*.py`, `scripts/*.sh`). It runs no hosted service and stores no user data. The main security concerns are:

- A secret, credential, or personal/client data that slipped past the publish-time leak gate (`scripts/scrub_gate.py`).
- A helper script that behaves unexpectedly or unsafely.
- A skill whose instructions could lead an agent to a harmful action.

## Reporting a vulnerability

Please report privately — **do not** open a public issue for a security problem.

1. Go to the repository's **Security** tab → **Report a vulnerability** (GitHub private vulnerability reporting), or
2. Use the **Report a vulnerability** button at <https://github.com/unfoldcro/cro-agent-skills/security/advisories/new>.

Include: the file and line, what the issue is, and how to reproduce or confirm it. If it's leaked sensitive data, name the exact string so we can scrub it.

## What to expect

- We aim to acknowledge within a few business days.
- Confirmed issues are fixed on a priority branch and released via a normal PR.
- Leaked-data reports are handled first: the content is removed and history rewritten if needed.
- Credit in the fix notes if you'd like it.

## Supported

Only the current `main` is maintained. There are no long-lived release branches.
