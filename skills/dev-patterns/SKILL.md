---
name: dev-patterns
description: House build patterns - auth/roles, payments (Razorpay/Stripe), webhooks, cron/jobs, file uploads, email/WhatsApp, audit log, multi-currency, API errors, LLM features. Use for "add auth", "add payments", "integrate <API>". NOT new-project setup (dev-kickoff) or agent orchestration (dev-agents).
argument-hint: "<feature to add> [project]"
---

# Dev Patterns

Task: $ARGUMENTS

House pattern library used mid-build: "how do we do X here". Pick → adapt → verify. Load only the reference(s) the task needs.

## Index

| Need | Load |
|---|---|
| login, SSO, allowlist, roles/permissions, page guards, Shopify app OAuth, WP caps | `references/auth-roles.md` |
| checkout, gateway, order states, refunds, reconciliation, GST invoice | `references/payments.md` |
| inbound webhook, cron, queue, background job, retries, dead letters, rate limits | `references/webhooks-jobs.md` |
| DB access, migrations, audit log, soft delete, UTC/money storage, uploads (R2/S3), backups | `references/data-files.md` |
| transactional email, WhatsApp/SMS, OTP delivery, notifications, Payload hooks | `references/messaging.md` |
| route vs server action, response shape, zod, errors, external API clients, caching | `references/api-errors.md` |
| ₹ lakh/crore vs Western formats, timezones, locales, hreflang, phone/address, consent | `references/i18n-markets.md` |
| LLM feature inside a client app | `references/ai-features.md` |

Cross-cutting features load several: checkout = payments + webhooks-jobs + messaging + data-files.

## Before picking

1. Read project `CLAUDE.md` + Docs map: stack, host (VPS/PM2 vs Vercel), ORM, auth lib, existing libs.
2. Grep repo for an existing implementation (`lib/auth*`, `*mail*`, `cron`, `webhook`, `money`, `storage`). Extend it; don't add a parallel one.
3. Sibling the agency project already solved it → copy the *pattern* only. Never its data, DB, creds or env values.
4. Smallest pattern that meets the need. No adapter interface for one provider, no Redis/queue infra for 10 jobs/day.
5. Stack fork: Next.js = default code shapes · WP/PHP + Shopify flagged per reference · other Node/PHP in Docker → adapt the Next shape.

## Adapting

- Keep the flow steps; swap code shape to the project's ORM, router, auth lib, naming (`agent.md` → Code Standards).
- Third-party accounts (gateway, SMTP, WhatsApp, Google Cloud, R2, LLM key) = **client-owned**, client email. Unknown → ask. the agency's own products exempt.
- Client code: client prefix or neutral names. No `org`/`the-org` in classes, IDs, files, comments.
- Secrets: env var NAMES only in code, docs, chat. Values → `.env` `FILL_ME` + hidden-input `set-secrets.sh` (`read -rsp`) the user runs on the target.
- `(verify)` = legal/tax/provider-limit claim. Confirm against current official docs (Context7 / provider docs) before shipping.
- React UI for the feature → Astryx + Motion. Never in WP/PHP/Liquid.

## Hard rules

- Server is source of truth: amount, price, role, status, ownership. Client input is a request, never a fact.
- Every protected page, route handler and server action guards itself. Middleware alone ≠ auth.
- Inbound events: verify + store + idempotent. Outbound calls: timeout + bounded retry.
- Store UTC. Money = integer minor units + currency code.
- No prod reset/drop/`--accept-data-loss`/`--force-reset`/DELETE without explicit OK + backup first.
- Code change → `build-review-loop`. Push/merge/deploy/prod data writes → explicit approval.
- Auth, payments, uploads, webhooks → focused `/security-audit` pass before go-live.

## Verify (every pattern)

- Name the end state first: "revoked user gets 401 on /orders", "webhook replayed 3× → 1 order, 1 email".
- Assert it on the real path (staging/live data, provider sandbox, headless browser with no cookies).
- Proxies are not proof: queue empty, `wp_mail()` true, SMTP `verify()`, CI green, `tsc` clean, "deploy success".
- Indirect check → say it's indirect.

## Point to, don't duplicate

- DB depth: `prisma-patterns`, `mysql-patterns`, `database-migrations` (project-scoped)
- LLM: `claude-api` (provider/model/params) · `cost-aware-llm-pipeline` (budgets/routing)
- File-processing cache: `content-hash-cache-pattern`
- Vercel runtime: `vercel:queues`, `vercel:workflow`, `vercel:vercel-functions`
- Shopify Admin scripts: `<templates>/shopify-admin-app` kit
- Standards: `~/.claude/agent.md` (Security, Response Shape, Error Handling, DB Safety, WP Rules)
