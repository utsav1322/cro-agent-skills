# Next.js / React: platform checklist

## Detect / record
- **Router:**
  - App Router: inline `self.__next_f.push(...)` RSC payload, `/_next/static/chunks/app/`.
  - Pages Router: `<script id="__NEXT_DATA__">` (check it for leaked props/PII too), `/_next/static/chunks/pages/`.
- **Version:** `window.next.version`, `x-powered-by: Next.js` (absent if `poweredByHeader:false`).
- **Host / cache:**
  - Vercel: `x-vercel-id`, `x-vercel-cache`, `server: Vercel`.
  - Self-host (nginx + PM2): `x-nextjs-cache` HIT / STALE / MISS, `x-nextjs-prerender`.
  - Cloudflare in front: `cf-cache-status`.
- **Render mode per template:** raw doc body contains copy + `<a href>` links + meta → SSR / SSG / ISR. An empty `<div id="root|__next">` shell → CSR. Mixed is common (SSR shell, content fetched client-side).
- **Other React-family stacks:**
  - Vite SPA: `<div id="root"></div>` + `/assets/index-<hash>.js` module.
  - CRA: `/static/js/main.*.js`.
  - Remix / React Router 7: `__remixContext` / `__reactRouterContext`.
  - Gatsby `___gatsby` · Astro `astro-island` · Nuxt `__NUXT__`, `/_nuxt/`.
- **Repo available (read-only)?** Read:
  - `app/layout.tsx` and the `generateMetadata` of each `page.tsx`.
  - `middleware.ts` / `proxy.ts` (Next ≥16 name).
  - `next.config.*`: `redirects`, `trailingSlash`, `htmlLimitedBots`, `images`.
  - `app/sitemap.ts`, `app/robots.ts`, and `public/` (static sitemap/robots shadows).
  - The API client's 401 handler.

## P0: indexability
- **Client-side auth bounce:**
  - Mechanism: the public page returns 200 with full meta, then hydration fires an API call → 401 → a global handler sends it to `/login`. curl can't see this; Googlebot renders and indexes the login page.
  - Test: headless Chromium, no cookies, `networkidle` + a settle delay. Is final URL == requested? PSI `finalUrl` and its redirects audit corroborate.
  - Suspect it when one route family has ~0 GSC impressions while a sibling family ranks.
  - Fix: the public-route allowlist in BOTH middleware/proxy AND the client handler, changed as a pair (comment each site).
- **Root-layout canonical cascade:** `alternates.canonical: '/'` in `app/layout.tsx` is shallow-merged into every page that lacks its own `alternates` → site-wide canonical = home.
  - Fix: remove it from root; set a per-page `alternates.canonical` in `generateMetadata`.
- **noindex leaks:**
  - (a) An explicit field-by-field data mapper drops `slug` / `seo` → `generateMetadata` takes its noindex branch (seen three times; check mappers first).
  - (b) `NEXT_PUBLIC_*` noindex flags are inlined at BUILD, so flipping the env without a rebuild keeps noindex.
  - (c) An nginx / host `X-Robots-Tag` set for staging survives cutover.
  - Check both meta and header on every template.
- **JS vs Google:**
  - A raw-HTML noindex that JS later removes doesn't work (Google may skip rendering).
  - Raw canonical must equal the rendered one.
- **Streaming metadata (Next ≥15.2):**
  - Dynamic `generateMetadata` → tags are appended in `<body>` for UAs not in `htmlLimitedBots`, which includes Googlebot.
  - Google honours canonical ONLY in `<head>`; robots meta in `<body>` is OK.
  - Test: raw HTML fetched with a Googlebot UA — is the canonical in `<head>`?
  - Fix if not: make the metadata prerenderable (static / `'use cache'`) or add Googlebot to `htmlLimitedBots` (TTFB trade-off).
- **SPA on a static host** (Vite / CRA on Render, Netlify, S3, Cloudflare Pages):
  - Non-prerendered routes get `index.html` → homepage title + `canonical=/` + 200 on every blog/detail URL, i.e. duplicates of home / soft-404s.
  - The local dev/Express server behaves differently from prod, so ALWAYS test LIVE raw HTML.
  - Fix: prerender every public route, keeping the host route list and the `vite.config` prerender routes in sync. Otherwise host rewrites with a real 404, or SSR.

## P1: status codes, redirects, URLs
- **Unknown URL → real 404** (`notFound()` / `not-found.tsx`), not a 200 soft-404 or a 307 → `/login`. Probe a static path AND a dynamic segment (`/blog/zz-<rand>`).
- **Redirect codes:**
  - `redirect()` = 307, `permanentRedirect()` = 308, `next.config` `redirects` with `permanent:true` = 308, middleware `NextResponse.redirect` default = 307.
  - Permanent moves must be 301/308. www ↔ apex should be one 308 hop. Watch for chains across middleware + config + host/CDN.
- **URL consistency:** `trailingSlash` = canonical = sitemap = internal links. Slug case and duplicate slugs should be canonicalised.
- **Vercel:** preview deployments get `x-robots-tag: noindex` by default (verify custom staging domains). The prod `*.vercel.app` alias → redirect to the custom domain.
- **i18n:**
  - Locale redirects driven by `Accept-Language` / geo in middleware mean Googlebot (no AL, US IP) never reaches other locales → every locale URL must 200 directly.
  - `alternates.languages` must be reciprocal and include `x-default`.

## P1: sitemap / robots
- **One source:** `app/sitemap.ts` vs `public/sitemap.xml`. A build-script output with a hard-coded www host and auth-gated URLs once shadowed the route → keep one. Same for `robots.ts` vs `public/robots.txt`.
- **Sitemap contents:** only 200, indexable, self-canonical prod-host URLs. Use `generateSitemaps` past 50k. Real `lastModified`.
- **`metadataBase`** = prod origin via env. Preview builds must not emit prod canonicals (or the reverse).

## P2: rendering / performance
- **Crawlable content:**
  - Content behind `useEffect` / client fetch, tab/accordion panels missing from the DOM.
  - Infinite scroll with no paginated `<a href>` URLs.
  - Navigation via `onClick` + `router.push` with no `<a href>` (`<Link>` is fine).
- **HTML weight:** App Router inlines the RSC payload (`__next_f`), which roughly duplicates content; Pages Router `__NEXT_DATA__` often carries whole API responses. Check raw bytes vs the 2MB cap on big listing pages.
- **LCP image:**
  - `next/image` hero with `loading="eager"` / `fetchPriority="high"` (`priority` is deprecated in Next 16 → `preload`), correct `sizes`, not inside a client-only carousel.
  - Bursts on the `/_next/image` optimizer can 502 a single self-hosted process → CDN cache rule for `/_next/image`, or pre-sized assets.
- **Caching:** ISR / `x-nextjs-cache: STALE` keeps old metadata until revalidate → note the cache state in evidence.
- **Fonts:** `next/font` (self-hosted) vs render-blocking Google Fonts CSS.

## P2: schema / meta ownership
- **JSON-LD:** render `<script type="application/ld+json">` from a Server Component, not client-injected. One emitter per type (layout + page duplicates are common).
- **Nested metadata:** `openGraph` / `robots` objects are REPLACED, not merged, by a child segment (a child setting `openGraph.title` loses the parent's images) → share via a spread constant.
- **Pages Router:** watch for duplicate `next/head` tags across `_app` / page.

## Security cross-check
- If `window.next.version` / React falls in a published RCE advisory range (e.g. the Dec-2025 React Server Components advisories), hand off to `security-audit`. A compromised box serving cloaked spam is an SEO incident too.

## Fix workflow (proposal; the owner executes)
- **PR-only**, one branch per fix. Never push main: main often auto-deploys (Vercel / Render), so a merge = a deploy. Deploy per the project's `docs/16-DEPLOYMENT.md` + approval.
- **Self-hosted:** changing a `NEXT_PUBLIC_*` value needs a rebuild (`rm -rf .next && npm run build`) → say so in the fix.
- **Verify after deploy:** headless Chromium on prod + PSI `finalUrl` + GSC URL Inspection.
- **UI changes** follow the project's component conventions. New code names stay neutral.

## Hand-off
- JS rendering depth / CWV → `seo-technical` · schema → `seo-schema` · hreflang → `seo-hreflang` · sitemap → `seo-sitemap` · CVE / hack → `security-audit`.
