---
name: backend-architecture
description: 'Backend architecture decisions mid-project: how should we architect, ERP/OMS sync, order sync, webhook reliability, idempotency, data model, ADR, scale this. Smallest design first. NOT new-project setup (dev-kickoff), NOT code patterns (dev-patterns), NOT UI/React (frontend-system-design).'
argument-hint: "<integration or decision to architect> [project]"
---

# backend-architecture

Decision: $ARGUMENTS

A reference and structured decision checklist for ONE hard backend call mid-project: which design, the trade-offs, an ADR, failure modes, and the idempotency / consistency / reconciliation decisions. Reference only. Writes no app code, installs nothing, deploys nothing.

## The gap this fills (do not duplicate these)

- `dev-kickoff` owns new-project intake, stack choice, scaffold and the first architecture docs. This skill is NOT project intake.
- `dev-patterns` owns the exact code shape for auth, payments, webhooks, jobs, DB, API. This skill decides WHICH design; `dev-patterns` builds it.
- `frontend-system-design` owns React/UI state and rendering. This skill is backend only.
- `technical-feasibility` answers "can it be built". Run it first if that is still open.
- `build-review-loop` owns coding + review. `task-dispatch` owns capability choice and the 80+ gate.

## When it fires (selective, no slash needed)

Fire only for a substantive backend design or review: Shopify/app to ERP or OMS order sync, payment/order lifecycle, multi-tenant data boundaries, a WordPress/Woo integration with jobs and retries, or a scale decision backed by real numbers.

Stay INACTIVE for: Shopify Liquid/theme edits, trivial CRUD, one-line API fixes, WordPress styling, UI work. If data-integrity or scale risk is not material, say so and hand back.

## Hard rules

1. Smallest viable architecture. Default is one service + one database + the managed platform's own features (cron, platform queue, managed Postgres). Never recommend microservices, a message broker, Redis, Kubernetes or a second datastore without measured evidence that requires it.
2. No invented numbers. Never present RPS, latency, cost, uptime or a provider API limit as fact. Mark every scale/limit/cost claim `(verify)` and check the provider's current official docs (Context7 or the provider's own page) before relying on it.
3. Evidence first. Read real constraints (users/traffic, data sensitivity, deploy + maintenance budget, integration contracts, failure tolerances). State what evidence is missing instead of assuming scale.
4. Server is the source of truth: amount, price, role, status, ownership. A client or an inbound payload is a request, never a fact.
5. Exactly-once BUSINESS EFFECT via idempotency; never promise exactly-once message delivery.
6. No app code written, nothing installed, nothing deployed, no destructive DB action. Approval gate before any implementation or production change.
7. Client-owned accounts and emails; no `org`/`the-org` in client code or identifiers; project docs stay local; secrets are env-var NAMES only. Verify the outcome, not a proxy (`verify-the-outcome-not-a-proxy`).
8. Original checklists only. Do not vendor or paraphrase copyrighted system-design material; develop from first principles.

## Lean process

1. **Constraints + evidence.** Restate the decision. List known numbers and failure tolerances; mark unknowns `(verify)`. Read the project `CLAUDE.md` + Docs map (stack, host, ORM, auth) and grep for an existing implementation to extend.
2. **Is review even needed?** If a single straightforward write covers it, say so and hand to `dev-patterns`. Otherwise continue.
3. **Describe the system.** Primary workflows, actors, trust boundaries, API/events, persistence, data ownership, and the failure points.
4. **At most TWO viable alternatives.** Trade-offs across complexity, cost, ops burden, consistency, latency and reversibility. Lead with the smaller one.
5. **Material cross-cutting concerns only.** Pull the reference(s) below for auth, tenant isolation, webhook signatures, idempotency, rate limits, retries, queues, transaction/consistency, migrations/backups, monitoring, recovery. Skip what does not apply.
6. **Output an ADR** (Context -> Decision -> Consequences), a mermaid flow when it clarifies, a failure-mode table, and testable acceptance checks. Label every item `planned` or `implemented`.
7. **Approval + hand off.** Get explicit approval before building. Then: project docs -> `dev-kickoff` / `setup-project-context`; exact code -> `dev-patterns`; build + review -> `build-review-loop`; release -> `deploy-runbook`.

## Reference index (load one on demand, never all)

| Need | Load |
|---|---|
| Inbound webhooks, ack + persist, dedupe, replays, idempotency, queue vs cron, scheduled jobs | `references/distributed-jobs.md` |
| Schema, indexes, transaction boundaries, consistency, tenant isolation, migrations, backup/restore | `references/data-architecture.md` |
| Payment/order state machine, reconciliation, duplicate events, refunds, auditability | `references/payments-and-integrity.md` |
| Provider quotas, backoff, 429/Retry-After, circuit breakers, pagination windows, timeouts | `references/api-and-rate-limits.md` |

## Output templates

```
ADR-NN: <decision>
Context: <constraints + evidence; (verify) items>
Decision: <chosen design, smallest that meets the need>
Alternatives: <A vs B, one trade-off line each>
Consequences: <cost, ops, reversibility; what we accept>
Status: proposed | accepted  ·  Approval: <who, pending/given>
```

| Failure mode | Likelihood | Blast radius | Detection | Mitigation | planned/implemented |
|---|---|---|---|---|---|

Acceptance checks: name the observable end state and assert it on the real path. e.g. "webhook delivered 3x -> 1 order, 1 email"; "revoked user gets 401 on /orders"; "tenant A query never returns tenant B rows"; "refund marked done only after the gateway confirms settled".
