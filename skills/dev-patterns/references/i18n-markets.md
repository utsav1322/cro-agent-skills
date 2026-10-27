# i18n + Markets

Implementation level only. Legal wording comes from the client / their counsel.

## Numbers + currency

- Format with `Intl`, by **audience locale**, not by currency.
  - `en-IN` → `₹1,23,45,678.00` (lakh/crore grouping). `en-US` → `$12,345,678.00`. `en-AE`, `en-GB` etc. per market.
  - Compact Indian: `new Intl.NumberFormat('en-IN', { notation: 'compact' })` → `12L`, `1.2Cr` style (verify output in target runtime; Node ICU differs).
- Store `amountMinor` + `currency`; divide by the currency's exponent at display.
- One money helper used everywhere. Hardcoded `₹` / `&#8377;` in templates breaks conversion (VN Codes).
- Multi-currency store: base price in one currency, market layer (currency, rate, rounding, gateway) recomputes server-side. Default market from GeoIP (nginx `geoip_country` / CF `CF-IPCountry`), cookie override, visible switcher. Report revenue in one base currency.
- Shopify: Markets does currency + hreflang. Currency-converter apps rewrite DOM `.money` elements, not Markets prices → JS-rendered prices need the app's class (verify per app).

```ts
// lib/format.ts
export const money = (minor: number, currency: string, locale = 'en-IN') => {
  const nf = new Intl.NumberFormat(locale, { style: 'currency', currency });
  return nf.format(minor / 10 ** (nf.resolvedOptions().maximumFractionDigits ?? 2));
};
export const formatDate = (d: Date | string, tz = 'Asia/Kolkata', locale = 'en-IN') =>
  new Intl.DateTimeFormat(locale, { timeZone: tz, day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(d));
export const dateKey = (d: Date, tz: string) => new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(d); // YYYY-MM-DD, internal only
```

## Dates + timezones

- Store UTC. Convert only at display.
- Indian audience / the agency products → IST + `DD/MM/YYYY` (or `24th May 2026`) per `rule.md` → Dates; React helper `formatIstDate`. Bans: `MM/DD/YYYY`, raw `YYYY-MM-DD` or `toISOString()` in UI.
- International client audience → their IANA TZ + locale format; record the decision in project docs. Use IANA names, never fixed offsets (DST).
- Per-user/per-store TZ: store IANA string; schedules and "today" computed in that TZ.
- Business-day logic (attendance, recurring, "one run per day") → `dateKey(now, businessTz)`.

## Locales + hreflang

- Next.js: `[locale]` segment or the project's i18n lib; `generateMetadata` → `alternates.canonical` (self) + `alternates.languages` incl. `x-default`. Reciprocal, only for real translated/market pages.
- WP: Polylang/WPML or theme hook on `wp_head`; one plugin owns hreflang.
- Shopify: Markets emits it; deleting a market → import 301s for its URL prefix.
- SEO depth → `seo-hreflang` skill.

## Phone + address

- Phone: store E.164 (`libphonenumber-js`, default country from market). India mobile = 10 digits starting 6–9. Display national format.
- Address: `line1, line2, city, state, postalCode, countryCode (ISO 3166-1 alpha-2)`.
  - India: 6-digit PIN, state from a list (state code feeds GST place of supply).
  - US: ZIP 5 / ZIP+4, state list. UK: postcode format. UAE: postcode often absent → optional (verify per market).
- Postcode required only where the market needs it. One "full name" field; don't force first/last split.

## Consent + cookies

| Regime | Mechanics (verify current rules) |
|---|---|
| India DPDP Act 2023 + Rules 2025 | Itemised notice; consent specific, unticked, recorded (`consent`, `consentAt`, notice version); withdrawal as easy as giving; data-principal request flow (access / correction / erasure / grievance / nomination); grievance contact published; breach notification. Phased commencement (verify dates). |
| EU/UK GDPR + ePrivacy | No non-essential cookies/pixels before opt-in; reject as easy as accept; granular categories; log consent; Google Consent Mode v2 for EEA traffic. |
| US (CCPA/CPRA etc.) | "Do Not Sell or Share" link, honour Global Privacy Control signal. |

Pattern:

- One consent store (cookie `consent = { v, analytics, marketing, ts }`) + server copy for logged-in users / orders.
- Single tag injector checks category before loading any pixel (the-org.com `tracking_scripts.consent_category`). No hardcoded pixels in layouts.
- Server-side events (GA4 MP, Meta/OpenAI CAPI) respect the consent flag stored with the order.
- Forms collecting personal data: notice + consent checkbox; persist consent with the record.
- Data-request page → `data_requests` table → admin triage screen → email notify (client-owned address).
- PII to third parties (analytics, LLM, CRM) only within consent + DPA. Hosting region if client requires residency.

## Verify

- [ ] Snapshot formats: `money(12345600,'INR')` → `₹1,23,456.00`; USD/AED in their locales.
- [ ] Dates around midnight UTC/IST show the right day in IST and in the client TZ.
- [ ] hreflang reciprocal + self-canonical in rendered HTML (headless).
- [ ] Fresh profile, no consent: no marketing/analytics requests in network log (chrome-devtools MCP). Reject → none after reload. Accept → tags load.
- [ ] Data request submitted → admin row + notification.
- [ ] Phone/address forms accept valid international inputs and reject junk.
