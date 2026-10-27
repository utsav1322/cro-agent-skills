# Data + Files

Depth: `prisma-patterns`, `mysql-patterns`, `database-migrations` (project-scoped). This file = house rules + lessons.

## DB access

- One server-only `lib/db.ts` client (Prisma singleton in dev). Serverless/pooled PG → pooled URL at runtime, direct URL for DDL (pgbouncer can't do DDL).
- Map rows → DTO; never return raw DB objects. Public ids = UUID/slug (`agent.md` → Security).
- No `await` inside loops on hot endpoints → `where: { id: { in } }` / `include`.
- Write filters positively. `NOT (…)` over nullable columns silently drops NULL rows — the ones that need attention.
- Shared business filters ("needs attention", "visible to user") defined once and imported everywhere.
- Multi-tenant: `tenantId` on every row, scoped helper, fail-closed when missing.

## Migrations

- Know the project's mode: `prisma db push` (no history; many the agency portals) vs `migrate deploy`. DB created by `db push` → `migrate deploy` errors P3005 → baseline (`migrate resolve --applied`) before switching. Don't mix silently.
- Never on prod: `migrate reset`, `migrate dev`, `--force-reset`, `--accept-data-loss`, DROP/TRUNCATE. Dev reset only with consent.
- Expand → backfill → contract. Destructive step = separate manual run with backup first, never riding a merge auto-deploy that runs `db push`.
- Prod column drift: `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.
- Prisma CLI on server: `set -a; . ./.env; set +a` first.
- Drizzle: `generate` + `migrate` for prod; `push` dev only (verify project convention).
- WP `dbDelta` silently skips columns it can't parse → schema-version option + guarded explicit `ALTER`. MariaDB: no `LIMIT` on multi-table DELETE → select ids first. `OPTIMIZE TABLE` after big deletes.
- Index on a large live table (1M+ rows) → ask first.

## Audit log

```prisma
model AuditLog {
  id        String   @id @default(uuid())
  actorId   String?
  action    String   // "order.status.update"
  entity    String
  entityId  String
  before    Json?
  after     Json?
  ip        String?
  createdAt DateTime @default(now())
  @@index([entity, entityId])
  @@index([createdAt])
}
```

- Write in the same transaction as the change. Mask secrets/PII in `before/after`.
- Admin-only read. Retention prune cron (e.g. 365 d).
- WP option-change log on `update_option` hooks misses cron/REST writes if it is admin-only. Know the gap.

## Soft delete

- `deletedAt` / `disabledAt` + default filter in data helpers; PG partial unique index `WHERE "deletedAt" IS NULL`. Users = tombstone; DPDP/GDPR erasure → separate hard-delete/anonymise path.

## Time

- Store UTC (`timestamptz` / UTC DATETIME). Server TZ UTC. Display via one helper (see i18n-markets).
- Mixed sources: WP `current_time('mysql')` (site-local) vs UTC rows → normalise before sorting (timeline interleaved wrong).
- Provider naive strings: confirm TZ (Shipmozo naive = UTC → append `Z`). Shopify order query with `+05:30` offset silently ignored → use `Z`, sanity-check with `ordersCount`.

## Money

- `amountMinor` integer (BIGINT) + `currency` CHAR(3). Never float. Exponent per currency (JPY 0, KWD/BHD 3).
- Base price in one currency; market layer converts; charge recomputed server-side. Snapshot FX rate + charged amount on the order.
- One breakdown function (subtotal, discount parts, tax, shipping, total) for checkout, invoice, email, admin.

## File uploads (R2/S3)

1. Client asks server: auth + declared type/size vs allowlist.
2. Server returns presigned PUT (≤5 min) with server key `prefix/yyyy/uuid.ext` (ext from MIME, never filename).
3. Client PUTs direct to bucket → calls confirm → server `HeadObject` checks size/type → DB row.
4. Serve private via presigned GET (short TTL, expiry bucketed to the hour so URLs stay cacheable); public via a dedicated media subdomain.
5. Delete row → delete object; storage error → fail loud, keep row (no silent orphans).

```ts
const s3 = new S3Client({ region: 'auto', endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId: process.env.R2_ACCESS_KEY_ID!, secretAccessKey: process.env.R2_SECRET_ACCESS_KEY! } });
const ALLOWED = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'application/pdf': 'pdf' } as const;
const MAX = 10 * 1024 * 1024;

export async function createUpload(type: string, size: number) {
  const ext = ALLOWED[type as keyof typeof ALLOWED];
  if (!ext || size <= 0 || size > MAX) throw new BadRequestError();
  const key = `uploads/${new Date().getUTCFullYear()}/${crypto.randomUUID()}.${ext}`;
  const url = await getSignedUrl(s3, new PutObjectCommand({ Bucket: process.env.R2_BUCKET, Key: key, ContentType: type, ContentLength: size }), { expiresIn: 300 });
  return { key, url };
}
```

Gotchas:

- R2 region = `auto`. Use a dedicated bucket-scoped R2 API token; a general CF token derived into S3 creds gets Access Denied.
- NEVER attach the app's own hostname as an R2 custom domain → whole site 404s (Space outage).
- Public custom domain = entire bucket world-readable by key. Private data (screenshots, invoices, IDs) → presigned only.
- `minio` client can't list >1000 objects → `rclone` for bulk copy/migrate.
- SVG uploads = XSS vector → reject or sanitise. Images: serve WebP thumbs, full file on demand.
- Write temp → `rename()`; validate by container end-marker, not `getimagesize()`.
- WP: image fields use the media picker, never a bare URL input. Protected files outside webroot or nginx-denied. Never `file.bak` copies in webroot (served as text).

## Backups

- Before any schema-touching deploy: `pg_dump "$DATABASE_URL" -Fc -f backups/pre-deploy-<ts>.dump` / `mysqldump --single-transaction`.
- Prod data → off-box copy (R2/B2/Drive; B2 needs a lifecycle rule). Success stamp + watchdog. Untested restore = no backup.
- Dumps hold PII + keys: mode 600, outside webroot, never committed, deleted when the migration is done.

## Verify

- [ ] Migration rehearsed on a copy of prod; row counts before = after for untouched tables.
- [ ] Each mutating action writes one audit row with actor.
- [ ] Wrong type / oversize / expired URL upload → rejected. Private object URL without signature → 403.
- [ ] Money: total in DB == gateway charge == invoice total for a test order with discount + tax + shipping.
- [ ] Restore drill succeeds; app boots against restored DB.
