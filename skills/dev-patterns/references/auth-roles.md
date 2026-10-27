# Auth + Roles

## Pick

| Situation | Pattern |
|---|---|
| Internal the agency tool, few known users | Google OAuth **reusing an existing the agency OAuth client** (Space/finance) + email allowlist in `signIn`. Add the new redirect URI to that client. |
| Sibling the agency product needs Space identities | Space = identity provider: roster API (Bearer key) + short-lived signed login token (60–120s, nonce). Target re-checks email is a live user, mints its OWN session. Never read Space's DB. |
| Client portal (staff + client users) | Client's own Google Cloud OAuth client. **DB = source of truth** (active user row admits); env allowlist = break-glass only. Roles → capabilities. |
| Partners/customers, no Google | Email OTP: hashed code, 10 min expiry, single use, verify rate-limited (5 / 10 min / email). |
| Shopify app | OAuth on permanent `*.myshopify.com` domain (below). |
| WordPress | Own capability per plugin + nonce (below). |

## Flow (Next.js portal)

1. Auth lib already in project (NextAuth v4 / Auth.js v5 / jose). `signIn` callback → allowed(email).
2. Cookie name unique per portal, host-only; own `AUTH_SECRET` per portal. Shared parent-domain cookie names collide (`.the-org.com` → `JWT_SESSION_ERROR`, 401 everywhere).
3. Middleware = first gate only (checks cookie signature). Prefer a **negative matcher** (everything except public) so new pages can't be forgotten. Exclude `/api/auth` from matcher + strict rate-limit buckets (session is polled).
4. **Every** page, layout-less route, route handler, server action calls `requireSession()` / `requireCapability()` itself. Layout checks are skipped on client navigation.
5. Roles → capability map in ONE file. Reads and writes are separate checks (`canView*` vs `canEdit*`); widening a read gate must not widen writes.
6. Row scoping helper is fail-closed: most-restricted role branch first; missing tenant/client id → impossible where-clause.
7. Remove user = `disabledAt` tombstone, never row delete (deleted row → falls back to env allowlist). Access writes keep ≥1 active super admin (serializable tx, fresh read).
8. Behind nginx/Apache: build redirects from `APP_URL`, never `req.nextUrl.origin` (resolves to `localhost:<port>`).
9. Cross-origin iframe SSO cookie → `SameSite=None; Secure`. `Lax` silently isn't set on the cross-origin redirect.

```ts
// src/lib/auth/roles.ts
export const ROLE_CAPS = {
  SUPER_ADMIN: ['*'], ADMIN: ['orders:write', 'users:manage'], OPERATOR: ['orders:write'], VIEWER: [],
} as const satisfies Record<string, readonly string[]>;
export type Role = keyof typeof ROLE_CAPS;
export const can = (r: Role, cap: string) =>
  (ROLE_CAPS[r] as readonly string[]).some((c) => c === '*' || c === cap);

// src/lib/auth/guard.ts
import 'server-only';
export async function requireSession() {
  const s = await auth();
  const email = s?.user?.email?.toLowerCase();
  const user = email ? await db.user.findFirst({ where: { email, disabledAt: null } }) : null;
  if (!user) redirect('/login');           // route handlers: return 401 JSON instead
  return user;
}
export async function requireCapability(cap: string) {
  const user = await requireSession();
  if (!can(user.role as Role, cap)) throw new ForbiddenError();
  return user;
}
// middleware.ts — add public marketing routes to the exclusion; webhooks/cron carry their own auth
export const config = { matcher: ['/((?!login|api/auth|api/webhooks|api/cron|_next|favicon.ico|.*\\.(?:png|jpg|svg|webp|ico)$).*)'] };
```

Public pages + client-side 401 handler: keep middleware public list and client "public pages" list in sync, comment each pointing at the other. A missed route hydrates → 401 → `/login` → Googlebot indexes the login page.

## Shopify app OAuth

- Authorize against the **permanent** domain (`Shopify.shop` in storefront HTML), not the admin slug → "Wrong store", no token.
- Verify `hmac` + `state` on callback. Store offline token encrypted, server-side only.
- Required scopes minimal; extras in `optional_scopes`. Avoid customer/order scopes unless needed (protected customer data review).
- `read_all_orders` needs Shopify approval; requested without it OAuth silently omits it → only last 60 days visible.
- Public apps: mandatory compliance webhooks `customers/data_request`, `customers/redact`, `shop/redact` (verify current list).
- Scripts on a client store: `templates/shopify-admin-app` kit. Client-credentials only in same org; collaborator → custom distribution + one-time offline token. Trust `check-access`, not the OAuth "granted" count.

## WordPress

- Own cap per plugin (`acme_manage_store`), granted to `manage_options` holders via filter. Never gate on `manage_options` itself (options.php escalation). "Client wants to see a screen" → add a view-only cap.
- Every admin POST / AJAX / REST write: cap check + nonce. REST write routes never `__return_true`.
- Anything HMAC-keyed off `wp_salt()` breaks on salt rotation → dedicated key constant in wp-config. Salt rotation ≠ revoking application passwords.
- Huge user tables (every customer = WP user): role/cap queries scan `usermeta` → `count_users()`, `who=>authors` hang admin. Cache or rewrite; `EXPLAIN` first.

```php
add_action('admin_post_acme_save', function () {
    if (!current_user_can('acme_manage_store')) wp_die('', 403);
    check_admin_referer('acme_save');
    // ...
});
register_rest_route('acme/v1', '/orders', [
    'methods' => 'POST', 'callback' => 'acme_create_order',
    'permission_callback' => fn () => current_user_can('acme_manage_store'),
]);
```

## Verify

- [ ] Signed out (headless, no cookies): each protected page → `/login`; each protected API → 401 JSON.
- [ ] Disabled user with a still-valid cookie → no data on next request: page, API, server action.
- [ ] Lower role → 403 on every mutation via **direct** POST (not just hidden button).
- [ ] Non-allowlisted Google account rejected. Redirect URI present on the OAuth client.
- [ ] Public pages: final URL == requested URL in headless render.
- [ ] Shopify: install on dev store via permanent domain; `check-access` lists expected scopes.
- [ ] WP: Client/Subscriber hitting admin-post + REST write → 403.
