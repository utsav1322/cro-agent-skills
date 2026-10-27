# distributed-jobs — webhooks, jobs, dedupe, idempotency

Reference for reliable inbound events and background work. Decide the SMALLEST design that holds; add a durable queue only when evidence (volume, long processing, provider timeouts) demands it. Checklists are original; verify every provider limit against current official docs and mark `(verify)`.

## Inbound webhook: ack vs persist

- Split "accept" from "process". Verify the signature, persist the raw event durably, return 2xx FAST, then process. Providers retry on a slow or non-2xx response, which multiplies load exactly when you are already slow.
- Do the real work after the ack: a background worker, a per-minute cron drain, or a platform queue — in that order of preference. A synchronous persist plus a cron sweep beats standing up a broker for low volume.
- Processing must be safe to run again: the same event may arrive two, three, or more times.

## Signatures and trust

- Verify HMAC/signature on every inbound event against the shared secret before trusting a byte. Reject on mismatch.
- Provider offers no signature (some shipping/panel webhooks do not): put a secret in the URL (`?token=`), and NEVER trust the payload — re-read the real state over the authenticated API and act on that. The push is only a nudge to go look.
- Never act on a client-supplied amount, status, price or ownership from a payload. Server/API is the source of truth.

## Idempotency and dedupe

- Idempotency protects the BUSINESS EFFECT, not message delivery. Assume at-least-once; make the downstream write a no-op on repeat.
- Dedupe key = the provider's own stable identifier (event id, gateway txn id, or the courier's RAW scan wording + timestamp). Do NOT derive the key from your normalised/mapped status — changing the mapping then changes the key and you get mass duplicates, while the old key silently drops real events. Re-key with a migration if the formula must change.
- Enforce it at the data layer: a `UNIQUE` constraint on the dedupe key (e.g. a signed ledger row) makes a repeat insert fail cleanly instead of double-crediting.
- A rejected/duplicate write must still advance the cursor (e.g. `nextCheckAt`) or the poller re-queries that item forever.

## Outbound calls, retries, backoff

- Every outbound call gets a timeout. A hung dependency otherwise exhausts workers.
- Retry is bounded and backed off (exponential + jitter); after N attempts move to a dead-letter row for a human, do not retry infinitely.
- Carry an idempotency key on any retried write so the retry cannot duplicate the effect.
- A channel-level block (e.g. a gateway returning "too many logins", a 429 with Retry-After) means pause the channel, not retry into it. See `api-and-rate-limits.md`.

## Provider-pin expiry (polling chains)

- When you poll a chain of providers and "pin" the one currently answering, the pin must EXPIRE after a silence window `(verify the window)`. A stale pin keeps serving old data and the chain never reaches the provider that has the real update.
- Compare freshness against the checkpoint's own provider timestamp, never against the pin — different providers run hours apart for the same record.

## Scheduled jobs

- WordPress `wp-cron` is request-triggered: on a low-traffic site it may not fire for hours. For anything time-sensitive use a real system cron hitting the endpoint, or Action Scheduler for Woo. State this in the ADR.
- A per-minute cron draining a DB-backed queue table (with a per-run budget) is a legitimate, cheap queue. It needs no broker.
- Guard a job against overlapping runs (a row mutex / lock timestamp) so a long run and the next tick do not double-process.

## Observability (minimum)

- One structured log line per event with the dedupe key, outcome, and attempt count. Keep a rolling processed/failed count.
- Verify the OUTCOME, not a proxy: an empty queue proves the retry loop stopped, not that the records updated. Assert the stored end state on real data.
