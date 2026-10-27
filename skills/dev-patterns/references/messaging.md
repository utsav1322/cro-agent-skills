# Messaging: Email, WhatsApp/SMS, Notifications

## Email: pick sender

| Situation | Pattern |
|---|---|
| Client has Zoho / Google Workspace / M365 | SMTP with an app password on a client mailbox (`<project>@<clientdomain>`), low volume. |
| Volume, delivery proof, bounces | Transactional API on client's account (Resend / Postmark / SES / ZeptoMail / Brevo) + delivery webhooks. |
| M365 tenant with Security Defaults | SMTP AUTH refused even with app password (`535 5.7.139`) → Microsoft Graph `sendMail` app-only (client_credentials). WP: short-circuit `pre_wp_mail`. |
| the agency's own products | the agency senders allowed. Client projects never. |

DNS (must pass before go-live):

- SPF includes the **actual** sending service. One SPF record only (two = permerror).
- DKIM selector published by that service. DMARC record present.
- Sending through an unauthorised relay under `p=quarantine` → spam folder while logs say "sent".
- Zoho: paid custom-domain org = `smtppro.zoho.<dc>`, free = `smtp.zoho.<dc>`; rolling hourly limit, not daily.

## Email: flow

1. Template registry in ONE place: key, trigger, recipient, subject. Admin page can render it ("what the shop sends, and when").
2. Critical single sends (OTP, receipt) may send inline; on failure → enqueue.
3. Everything else → `EmailQueue` row → cron drain with budget (per-minute + rolling 24h, reserved share for high priority). Limits in DB settings, not code.
4. Pool SMTP connections. Gmail `454 Too many login attempts` = login per message → pool; treat 454 as channel block, pause 15 min.
5. Record the server's real verdict (`250` accepted / failed). SMTP accept ≠ inbox delivery; only provider webhooks prove delivery.
6. Dedupe/delay where useful (welcome delayed 8 h, cancelled if a purchase email goes).
7. Marketing mail: opt-in, unsubscribe link, per-user preferences default OFF for high-volume digests.

```ts
// lib/mail.ts
const transport = nodemailer.createTransport({
  host: process.env.SMTP_HOST, port: Number(process.env.SMTP_PORT ?? 465), secure: true,
  pool: true, maxConnections: 2, auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
});
export const queueEmail = (to: string, template: TemplateKey, vars: Record<string, string>, priority = 0) =>
  db.emailQueue.create({ data: { to, template, vars, priority, status: 'PENDING' } });
// drain cron: budget check → render → transport.sendMail → store response code → retry/pause rules (webhooks-jobs.md)
```

```php
// WP: SMTP config from constants/env, never plaintext DB options
add_action('phpmailer_init', function ($m) {
    $m->isSMTP(); $m->Host = ACME_SMTP_HOST; $m->Port = 465; $m->SMTPSecure = 'ssl';
    $m->SMTPAuth = true; $m->Username = ACME_SMTP_USER; $m->Password = getenv('ACME_SMTP_PASS');
});
```

Gotchas:

- Log/console fallback in prod printed live sign-in codes on the public login page. Dev = log driver; prod = real send or fail loud.
- Empty SMTP password during a provider switch hard-fails every send (lost a purchase delivery email).
- `transporter.verify()` passed for a password Gmail then rejected. Only a real send proves it.
- WP mail loggers that write "sent" on the `wp_mail` filter run before sending → record status after.
- `.gitignore logs/` swallowed a route folder named `logs` → name it `mail-logs`.

## WhatsApp / SMS

India:

- Provider on **client's** account (MSG91 / Gupshup / Interakt / 11za / WATI). Keys + template ids are account-scoped → everything on one account.
- WhatsApp templates are Meta-approved, plain text, positional variables → own template store; don't reuse email bodies.
- Categories: UTILITY (transactional), AUTHENTICATION (OTP), MARKETING (needs recipient opt-in, else "Failed by Meta").
- Messaging tier limit (e.g. 250 unique users / 24 h unverified) → Meta business verification to raise.
- SMS needs DLT: registered entity, sender header, content templates; text must match template (verify).
- OTP cascade WhatsApp → SMS → email, each tier activated per env (`*_TEMPLATE_ID` set = on), dormant otherwise.

International: Meta Cloud API or Twilio for WhatsApp; US SMS needs A2P 10DLC registration (verify).

Common:

- Store phones E.164. Normalise on input.
- "Every email gets a WhatsApp twin" = same trigger, separate template.
- Delivery/read receipts via provider webhook (webhooks-jobs.md).

## In-app notifications

- `Notification` table + unread count; email/push optional per type.
- Cap nudges (e.g. max 2/day, business hours only). Avoid hourly push storms.
- Removing web push: ship a self-unregistering `sw.js` tombstone; don't delete the file.

## Payload CMS

- Any `req.payload.find/update/count` inside a hook or access fn must pass `req` → else second transaction waits on outer locks → silent 30s hang.
- `versions` on → set `access.readVersions` or every logged-in user reads drafts.

## Verify

- [ ] Real send to a test inbox: lands in inbox; headers show `spf=pass dkim=pass dmarc=pass`; From is the client domain.
- [ ] Queue: forced failure → retry/pause; re-run cron → no duplicate sends.
- [ ] WhatsApp utility template delivered AND read on a real number; marketing without opt-in handled.
- [ ] OTP never visible in UI, logs or API responses in prod; verify endpoint rate-limited.
- [ ] Payload: admin save with hooks completes in <1 s.
