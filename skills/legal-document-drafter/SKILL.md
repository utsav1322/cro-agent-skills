---
name: legal-document-drafter
description: 'Draft working copies of legal documents (privacy policy, terms, refund policy, NDA, service agreement) from verified jurisdiction facts, with placeholders and a counsel-review flag. Use for "draft terms", "write a privacy policy", "draft an NDA". NOT reviewing a received contract (contract-check).'
---

# legal-document-drafter

## Purpose
Draft reviewable legal document working copies. Use concrete evidence and project-specific constraints. Do not claim work was executed, tested, legally approved, or verified unless it actually was.

## Activation
Activate when the request concerns draft reviewable legal document working copies. Read relevant project instructions first. When current laws, platform APIs, or tool capabilities matter, check authoritative current sources.

## Procedure
1. Start from verified jurisdiction facts.
2. State parties roles definitions and scope.
3. Avoid invented enforcement claims or implied attorney review.
4. Include placeholders for unknowns and version history.
5. Mark counsel review required.

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
