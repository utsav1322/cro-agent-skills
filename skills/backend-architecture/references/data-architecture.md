# data-architecture — schema, transactions, tenancy, migrations, restore

Reference for the persistence design. Default to one managed relational database; add a second datastore only on measured need. Original checklists; verify engine-specific behaviour against current docs and mark `(verify)`.

## Model and ownership

- Model the real entities and who OWNS each row before indexes or tech. Every row that belongs to a tenant/customer/user carries that owner id as a column.
- Decide the system of record for each field. If another system authors it (accounting totals, gateway status), store a copy with provenance columns (source, synced-at) and do not let the copy drift silently.

## Indexes and query shape

- Index the columns you filter and join on. `EXPLAIN` the hot queries before blaming a plugin, the browser or the host for "slow admin".
- Never make a hot path query a serialized/unindexable column at scale. A role/capability stored as serialized text (classic WordPress `usermeta`) forces a full-table `LIKE` scan; at hundreds of thousands of rows that is seconds-to-minutes and no index can seek it. Rewrite the query to hit an indexed column (e.g. a join on published posts) or add a real index as an approved, backed-up schema change.
- `SQL_CALC_FOUND_ROWS` / unconditional exact counts defeat `LIMIT` — the engine visits every matching row regardless of page size. Compute an exact total only when it is actually needed.

## Transaction boundaries

- Keep a logical operation in ONE transaction. Nested data calls inside a hook/callback must run on the SAME connection/transaction as the outer operation, or they open a second connection that blocks on the outer row locks and stalls for the full timeout — a symptom that reads like a slow database, not a bug (Payload: pass `req`; raw SQL: pass the same client/tx).
- Keep transactions short. Do no network I/O (a payment call, an email) inside an open transaction.
- Serialize invariant-critical writes (e.g. "always keep one active owner") in a transaction on a fresh read, not on cached state.

## Money, time, consistency

- Money = integer minor units + an explicit currency code. Never float.
- Store UTC; convert at the edge. When merging rows from two sources (DB rows in UTC, a mail/log table in local time), normalise both before sorting or the timeline is wrong.
- State the consistency you need per read: most portal reads tolerate read-after-write on the primary; only reach for a replica when load is measured, and then expect replica lag.

## Multi-tenant isolation

- Every query is scoped by owner/tenant; do not rely on the UI to filter. Test with TWO tenants and assert tenant A can never read or write tenant B's rows.
- Gate READS and WRITES separately. One permission check reused for both silently grants write access when you widen it to fix a read 403.
- Enforce the session/role on every page, route handler and server action. Edge middleware only checks the cookie signature; a revoked user keeps reading until the server actually re-checks. A CI guard that asserts every protected page calls the check is cheap insurance.

## Migrations

- Additive and forward-only by default: new table/column with `IF NOT EXISTS`, backfill, then switch. Never drop or rewrite a column on production without a backup and explicit approval.
- Confirm the deploy actually RUNS migrations. A build step (`next build`) does not run `drizzle-kit push`/`prisma migrate`; new tables then never exist in prod and routes 500. Column drift bites the same way — prefer `ADD COLUMN IF NOT EXISTS`.
- A safe auto-push (e.g. `prisma db push` without `--accept-data-loss`) should ABORT a destructive change rather than touch live data.

## Backup and restore

- A backup is unproven until a restore is tested. Name the RPO (data you can lose) and RTO (time to recover) with the client `(verify budget)`; a nightly dump nobody has restored is not a recovery plan.
- "Delete" = tombstone (a `disabledAt`/`deletedAt` flag), not a row delete, wherever a hard delete would re-admit access or orphan references. Keep an audit/activity trail for sensitive mutations.
