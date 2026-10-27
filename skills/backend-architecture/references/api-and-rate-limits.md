# api-and-rate-limits — quotas, backoff, breakers, timeouts

Reference for talking to a third-party or your own API under limits. Keep the design simple; a client-side cap plus bounded backoff handles most agency workloads without extra infrastructure. NEVER invent a limit — read the provider's current official docs and mark `(verify)`.

## Know the real limits

- Look up the provider's rate limit, burst allowance, and reset window from its OWN current documentation before designing. Do not quote a number from memory.
- Example (confirmed for one project, still `(verify)` against the provider): a shipping API enforced 240 requests/minute per IP. Treat every such figure as project- and plan-specific.
- Record the limit, its unit (per IP? per key? per shop?), and the reset semantics in the ADR.

## Stay under the quota

- Cap your own request rate BELOW the quota (e.g. 220 of a 240/min limit) with a sliding window, so bursts plus retries never cross the line.
- Batch where the API supports it; coalesce N small calls into one. Cache idempotent reads when the data tolerates slight staleness.

## Backoff and 429

- On 429 or 5xx, back off exponentially with jitter, bounded by a max attempt count. Honour `Retry-After` when present.
- Distinguish a per-request throttle (retry after backoff) from a CHANNEL-LEVEL block (e.g. an auth/login lockout, "too many logins"): a channel block means PAUSE the whole channel for a cool-off window, not retry into it, or you deepen the lockout.

## Circuit breaker

- Only add a breaker when a dependency actually flaps. When it does: after K consecutive failures, open the circuit (fail fast / queue for later) for a cool-off, then half-open to test. This protects your workers from a dead dependency; it is not needed for a dependency that is simply rate-limited.

## Pagination and data windows

- Many APIs expose only a recent window by default (e.g. a store API returning only the last ~60 days of orders without an elevated scope) `(verify)`. Beyond the window the API returns NOTHING, not an error — your copy silently freezes on the day a record ages out, and later updates never arrive.
- Know which scope/approval lifts the window and request it; until granted, design around the gap (snapshot in time, reconcile) rather than assuming full history.
- Use cursor pagination over offset for large or changing result sets.

## Timeouts and idempotency

- Every outbound call has a connect and a read timeout. A missing timeout turns one slow dependency into exhausted workers.
- Any write you might retry carries an idempotency key so the retry cannot duplicate the effect (see `distributed-jobs.md`).

## Do not rate-limit your own auth polling

- Session endpoints get polled by the framework on mount and window focus (e.g. NextAuth hitting `/api/auth/session`). Putting them behind a strict per-minute bucket 429s real signed-in users. Exclude auth/session routes from aggressive limiting.

## Capacity math — only when it is warranted

- Do capacity estimation only when workload or scale makes it relevant, and keep ASSUMPTION separate from MEASUREMENT. Write "assume ~X orders/day (verify)" rather than presenting a number as fact.
- If the numbers do not justify caching, a queue, a replica or an index, say so and keep the smallest design.
