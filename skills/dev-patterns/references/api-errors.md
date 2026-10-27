# API Shape, Errors, External Clients, Caching

Canonical: `~/.claude/agent.md` → Security (never-expose list), Standard Response Shape, Error Handling. This file applies it; it does not override it.

- Success `{ data }` · list `{ data, meta: { total, page } }` · error `{ error: string }` (generic to client, detail in server log).
- Never expose: stack traces, raw SQL/ORM errors, internal ids, tokens/keys, file paths, server info, password hashes, full emails on public endpoints.
- try/catch on ALL route handlers and server actions. Map DB rows → DTO.

## Route handler vs server action

| Use | For |
|---|---|
| Server Component data fetch | Page reads (data never hits the Network tab) |
| Server Action | Mutations from own UI. Still a public POST endpoint → auth + validate inside every action |
| Route Handler | Webhooks, cron, public/3rd-party API, Electron/mobile clients, file streaming |

## Shape

```ts
// lib/http.ts
export class HttpError extends Error { constructor(public status: number, public publicMsg: string) { super(publicMsg); } }
export class BadRequestError extends HttpError { constructor() { super(400, 'Invalid input'); } }
export class ForbiddenError extends HttpError { constructor() { super(403, 'Forbidden'); } }
export function handleError(e: unknown, route: string) {
  if (e instanceof HttpError) return NextResponse.json({ error: e.publicMsg }, { status: e.status });
  console.error(`[API] ${route}:`, e);
  return NextResponse.json({ error: 'Something went wrong' }, { status: 500 });
}

// app/api/leads/route.ts
const CreateLead = z.object({
  name: z.string().trim().min(1).max(120),
  email: z.string().trim().toLowerCase().email(),
  phone: z.string().regex(/^\+[1-9]\d{7,14}$/).optional(),   // E.164
});
export async function POST(req: Request) {
  try {
    const user = await requireCapability('leads:write');
    const parsed = CreateLead.safeParse(await req.json().catch(() => null));
    if (!parsed.success) throw new BadRequestError();
    const lead = await createLead(user, parsed.data);
    return NextResponse.json({ data: toLeadDto(lead) }, { status: 201 });
  } catch (e) { return handleError(e, '/api/leads'); }
}

// server action
'use server';
export async function setOrderStatus(input: unknown) {
  try {
    const user = await requireCapability('orders:write');
    const { id, status } = SetStatus.parse(input);
    await transitionOrder(user, id, status);
    revalidatePath('/orders');
    return { data: true };
  } catch (e) {
    unstable_rethrow(e);                        // let redirect()/notFound() through (Next 15; verify version)
    console.error('[action] setOrderStatus', e);
    return { error: e instanceof HttpError ? e.publicMsg : 'Something went wrong' };
  }
}
```

- Validate every boundary (body, query, params, webhook payload, env at boot). Field-level errors only if the project already returns them; `error: string` stays primary.

## Rate limits + headers

- Limit login/OTP, forms, public APIs, AI endpoints (not `/api/auth/session`). In-memory = one process only; PM2 cluster / multi-instance → DB/Redis store.
- Behind Cloudflare: real IP only after nginx `real_ip_header CF-Connecting-IP` + CF ranges, else every client = edge IP.
- Security headers per `agent.md`. Cross-app embed: CSP `frame-ancestors` on the framed app; remove `X-Frame-Options` in every layer (next.config AND nginx).

## External API clients

- One module per provider (`lib/<provider>.ts`): base URL, auth, timeout, retry, typed errors, redacted logs. Token refresh cached until expiry, single-flight.
- Retry only 429/5xx/network, backoff + jitter, honour `Retry-After`, max 3–5. Non-idempotent POST retried only with an idempotency key.

```ts
export async function fetchJson<T>(url: string, init: RequestInit = {}, tries = 4): Promise<T> {
  for (let i = 0; ; i++) {
    let res: Response | undefined;
    try { res = await fetch(url, { ...init, signal: AbortSignal.timeout(10_000) }); }
    catch (e) { if (i >= tries - 1) throw e; }                       // network/timeout
    if (res?.ok) return (await res.json()) as T;
    if (res && (![429, 500, 502, 503, 504].includes(res.status) || i >= tries - 1)) throw new ExternalApiError(res.status, url);
    const ra = Number(res?.headers.get('retry-after'));
    await new Promise((r) => setTimeout(r, ra > 0 ? ra * 1000 : Math.min(30_000, 500 * 2 ** i) + Math.random() * 250));
  }
}
```

Provider notes:

- **Shopify Admin GraphQL**: pin API version. HTTP 200 can carry `userErrors` / `errors` → check both. Cost throttle → back off on `THROTTLED`. Cursor-paginate (`first` caps at 250); Bulk Operations for big exports. Some mutations need `@idempotent(key:)` (e.g. `inventorySetQuantities`, 2026-07). Date filters with `+05:30` silently ignored → UTC `Z`.
- **Google APIs**: `PERMISSION_DENIED` → read `details[0].reason`: `SERVICE_DISABLED` = enable API; `API_KEY_SERVICE_BLOCKED` = add API to the key's restriction list. Keys may be IP-restricted. Sensitive scopes (GSC/GA4 read) need Google app verification → plan for the delay.
- **Apps Script web app**: access must be "Anyone"; Workspace-scoped silently 302s anonymous callers to login. Probe with cookie-less `curl -D -`.
- **Zoho (Books/Mail)**: data-centre-specific domains (verify .in vs .com); self-client refresh token; `organization_id` picks test vs live org (invoices once went to a test org); binary PDF needs a raw call, not the JSON client.
- **Merchant/user-supplied URLs**: own fetcher, HTTPS only, manual redirects, host allowlist (SSRF).
- **Behind proxy**: absolute URLs from `APP_URL`.

## Caching

- Org-wide reference data → Next Data Cache `revalidate` (60–300 s) / SWR client cache. User/permission-scoped → `no-store`; never edge-cache session-dependent `/api/*`.
- Slow aggregates over huge tables → stale-while-revalidate (transient / DB row). File processing → `content-hash-cache-pattern`. Signed URLs → bucketed expiry so they cache.

## Verify

- [ ] `curl` invalid body → 400 `{ "error": "Invalid input" }`; no stack/SQL/path anywhere in body or headers.
- [ ] No session → 401; wrong role → 403 (direct request, not UI).
- [ ] Response JSON contains only DTO fields.
- [ ] Mock provider 429/500/timeout → retries with backoff, then clean error; request time bounded.
- [ ] `next build` passes (tsc alone missed a webpack-only error).
