---
name: secrets-credential-manager
description: 'Keep secrets out of chat, code, docs and git: managed storage, environment separation, leak scans of diffs and history without copying values, rotation and revocation. Use for "leaked key", "rotate token", "where to store secrets", ".env". NOT hacked-site response (site-incident).'
---

# secrets-credential-manager

## Purpose
Prevent credential and secret exposure. Use concrete evidence and project-specific constraints. Do not claim work was executed, tested, legally approved, or verified unless it actually was.

## Activation
Activate when the request concerns prevent credential and secret exposure. Read relevant project instructions first. When current laws, platform APIs, or tool capabilities matter, check authoritative current sources.

## Procedure
1. Never request live passwords or secrets in chat.
2. Use managed secret storage and environment separation.
3. Scan diffs and history for accidental leaks without copying values.
4. Rotate exposed credentials and revoke tokens.
5. Check least privilege and audit logs.

## Verification gate
- State what was examined, what was not accessible, and any assumptions.
- Separate confirmed findings, risks, recommendations, and unverified hypotheses.
- For development, require relevant automated tests and manual checks before marking complete.
- Provide exact file paths/line references, data sources, or legal citations when appropriate.
- Report blockers and proposed fixes by severity. Never silently change production systems.

## the agency editorial and safety rules
- Write directly and specifically. No generic AI fluff, em dashes, exaggerated claims, artificial case studies, unnecessary dividers, or fabricated proof.
- Never reveal client secrets or personally identifying data unnecessarily. Use redacted examples and placeholders.
- Seek explicit approval before sending external communication, changing production, deploying code, deleting data, or conducting active security tests.
- For regulated legal or tax conclusions, provide research support, not a claim of professional sign-off.

## Deliverable template
1. Scope and context, 2. Evidence and findings, 3. Prioritized action plan, 4. Validation/acceptance criteria, 5. Uncertainties or approvals needed. Adapt format to the actual request rather than forcing five headings.
