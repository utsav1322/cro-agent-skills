# Webhooks + Jobs

## Inbound webhook flow

1. One route per provider: `/api/webhooks/<provider>`. Outside auth middleware, Node runtime (raw body + crypto).
2. Read raw body FIRST (`await req.text()`), verify signature with timing-safe compare; check timestamp tolerance if the provider signs one (Stripe 5 min).
3. Store raw event: unique `(provider, eventId)`. Duplicate insert → return 200, do nothing.
4. Ack fast (2xx well inside provider timeout; Shopify ~5s (verify)). Heavy work async.
5. Processor idempotent: conditional updates, unique keys, re-read authoritative state from provider API when payload is partial or untrusted.
6. A sweeper picks rows with `processedAt IS NULL` → crash between ack and processing loses nothing. Stored row is the guarantee, not the in-request call.

| Provider | Signature | Dedupe id |
|---|---|---|
| Shopify | `X-Shopify-Hmac-Sha256` = base64 HMAC-SHA256(raw, app secret / admin-UI signing secret) | `X-Shopify-Webhook-Id` |
| Razorpay | `X-Razorpay-Signature` = hex HMAC-SHA256(raw, webhook secret) | `x-razorpay-event-id` (verify) |
| Stripe | `stripe.webhooks.constructEvent(raw, sig, secret)` | `event.id` |
| Unsigned (Shipmozo, form beacons, Apps Script) | secret `?token=` in URL | re-fetch status via authenticated API; never trust payload |

```ts
// app/api/webhooks/shopify/route.ts
export const runtime = 'nodejs';
const safeEq = (a: string, b: string) => { const x = Buffer.from(a), y = Buffer.from(b); return x.length === y.length && timingSafeEqual(x, y); };

export async function POST(req: Request) {
  const raw = await req.text();
  const digest = createHmac('sha256', process.env.SHOPIFY_WEBHOOK_SECRET!).update(raw, 'utf8').digest('base64');
  if (!safeEq(req.headers.get('x-shopify-hmac-sha256') ?? '', digest)) return new Response(null, { status: 401 });
  const eventId = req.headers.get('x-shopify-webhook-id');
  if (!eventId) return new Response(null, { status: 400 });
  await db.webhookEvent.createMany({
    data: [{ provider: 'shopify', eventId, topic: req.headers.get('x-shopify-topic') ?? '', payload: raw }],
    skipDuplicates: true,                       // unique(provider, eventId)
  });
  return new Response(null, { status: 200 });  // worker/sweeper processes; on Vercel use after() or a queue (verify)
}
```

WP: `register_rest_route` with signature check inside `permission_callback`; `hash_equals()`; store in a custom table with UNIQUE event id; process via `wp_schedule_single_event`.

Webhook gotchas:

- Register every topic you depend on. Only `products/create` registered → product edits never repriced.
- Shopify admin-UI webhooks don't appear in the API webhook list; signing secret is on that admin page.
- Unsigned provider panels (Shipmozo): no secret/header option → URL token + re-read via API.
- Dedupe key from the provider's raw fields, not your normalised status — remapping statuses changed keys → mass duplicates.

## Jobs / cron by host

| Host | Pattern |
|---|---|
| VPS + PM2 | System crontab → wrapper script that loads `CRON_SECRET` from app `.env` (keeps it off `crontab -l`) → `curl http://127.0.0.1:<port>/api/cron/<job>` with Bearer. Address localhost port, not domain/PM2 name. `flock -n` against overlap. |
| VPS long work | Separate PM2 process `<app>-worker` polling a jobs table (`FOR UPDATE SKIP LOCKED`). BullMQ/Redis only if Redis already exists. |
| WP in Docker | Host cron every minute: `flock -n /tmp/<site>-wpcron.lock docker exec -u www-data <ctr> php /var/www/html/wp-cron.php` + `DISABLE_WP_CRON`. |
| WP plugin | `wp_schedule_event`; also schedule on `init` if missing (activation-only scheduling never runs on late installs). |
| Hostinger shared | No `crontab` binary → hPanel cron. Watchdog elsewhere. |
| Vercel | `vercel.json` crons (UTC, plan limits (verify)); route checks `Authorization: Bearer ${CRON_SECRET}`. Durable/queued → `vercel:queues` / `vercel:workflow`. |

Crontab lives outside git → record each line in `docs/16-DEPLOYMENT.md` + a repo `infra/cron` file. First suspect when "it stopped".

## Job rules

- Idempotent per run key: unique `(jobKey, dateKey)` / `@@unique([recurringId, date])`; `createMany skipDuplicates`; atomic claim `UPDATE … SET claimedAt=now() WHERE id=? AND claimedAt IS NULL`.
- Compute business day/TZ inside the job (IST dateKey) → crontab TZ irrelevant.
- Batch + cursor (e.g. 500/run); finish inside the interval.
- Retries: exponential backoff + jitter, max attempts (e.g. 1m, 5m, 30m, 2h, 12h) → `status=DEAD` + alert + admin list with Retry button.
- Channel-level failure (SMTP 454, provider 429/auth) → pause the channel N min; don't retry each item into it.
- A rejected/failed write still advances `nextCheckAt` (else re-queried forever). Provider "pins" expire.
- Every failure path records `lastError` somewhere visible.
- Outbound limits: sliding window under the published limit (Shipmozo 240/min/IP → cap 220). Shopify GraphQL cost throttle → back off on `THROTTLED`. Honour `Retry-After`.
- Heartbeat: write success stamp; separate watchdog alerts if no success in N h (B2 backup failed 16 days silently). Critical watchdogs run on a different host.
- Leaked `CRON_SECRET` (printed by `crontab -l`, chat) → rotate in `.env` AND every crontab line together.

```ts
// app/api/cron/<job>/route.ts
export async function GET(req: Request) {
  if (req.headers.get('authorization') !== `Bearer ${process.env.CRON_SECRET}`) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const due = await db.job.findMany({ where: { status: 'PENDING', runAt: { lte: new Date() } }, take: 500 });
  for (const j of due) {
    const claimed = await db.job.updateMany({ where: { id: j.id, status: 'PENDING' }, data: { status: 'RUNNING' } });
    if (!claimed.count) continue;
    try { await handlers[j.type](j.payload); await db.job.update({ where: { id: j.id }, data: { status: 'DONE' } }); }
    catch (e) {
      const dead = j.attempts + 1 >= 5;
      await db.job.update({ where: { id: j.id }, data: { status: dead ? 'DEAD' : 'PENDING', attempts: { increment: 1 },
        runAt: new Date(Date.now() + 60_000 * 4 ** j.attempts), lastError: String(e).slice(0, 500) } });
    }
  }
  return NextResponse.json({ data: { processed: due.length } });
}
```

## Verify

- [ ] Bad signature → 401, no row. Missing id → 400.
- [ ] Same event replayed twice → one side effect.
- [ ] Kill the app after ack → sweeper completes the event.
- [ ] Cron route without secret → 401; with secret → 200 + expected rows; run twice same day → no dupes.
- [ ] Crontab line present on the box (`crontab -l | grep <job>`, never print secrets); success stamp moves next day.
- [ ] Force provider 429/500 → retries scheduled → DEAD + alert after max.
