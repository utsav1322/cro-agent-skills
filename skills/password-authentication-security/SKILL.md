---
name: password-authentication-security
description: 'Audit login and password flows without handling real passwords: policy, breached-password checks, Argon2id or bcrypt hashing, MFA, rate limits, lockout, reset and session lifecycle. Use for "password policy", "login security", "MFA", "auth audit". NOT building auth (dev-patterns).'
---

# password-authentication-security

## Purpose
Audit password policy and authentication lifecycles. Use concrete evidence and project-specific constraints. Do not claim work was executed, tested, legally approved, or verified unless it actually was.

## Activation
Activate when the request concerns audit password policy and authentication lifecycles. Read relevant project instructions first. When current laws, platform APIs, or tool capabilities matter, check authoritative current sources.

## Procedure
1. Never collect plaintext passwords or full hashes.
2. Favor password managers long passphrases and breached-password blocklists.
3. Use Argon2id or appropriate adaptive salted hashing and verify implementation.
4. Check MFA rate limiting reset enumeration resistance and session revocation.
5. Validate against current NIST 800-63B and OWASP guidance.

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
