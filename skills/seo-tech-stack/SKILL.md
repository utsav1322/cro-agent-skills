---
name: seo-tech-stack
description: 'Detect site stack (Shopify, WordPress/Elementor/Woo, Next.js, Framer/Webflow) from the live page; run stack-specific tech-SEO checks + fixes. Use for "what is this site built on", "tech stack", "Shopify SEO issues", "WordPress technical SEO", "Next.js SEO". Generic audit → seo-technical/audit-site.'
argument-hint: "<url> [shopify|wordpress|nextjs|other]"
---

# seo-tech-stack: platform layer of technical SEO

Target: $ARGUMENTS

Detect stack from LIVE page → run that platform's checklist → findings with exact file / setting / app fix. Sample templates, don't crawl.
Generic 9-category audit = `seo-technical`. Full crawl + client deck = `audit-site`. This skill covers the platform quirks those two miss.

## Hard rules
- **Step 0 always:** fetch https://developers.google.com/search/updates and diff against the baseline below. Report line: `Google Search updates checked (DD/MM/YYYY)`.
- **Evidence only:** every finding = URL + what was observed (header / DOM node / request / status / file:line). No "probably". Unknown → say unknown.
- **Read-only:** never edit live theme/site/settings, purge caches, toggle apps or push. Pulling a theme or reading a repo locally is fine. Fixes = proposals routed through the project's own workflow (§5).
- **No `org` / `the-org`** in suggested client code: new snippet / file / ID / CSS class / comment names stay neutral (`snippets/seo-head.liquid`).
- **Known client domain** → read the project's `CLAUDE.md` + memory note first (live theme ID, cache layers, workflow, past gotchas). Don't re-derive.
- **Tracking/pixel inventory:** the chrome-devtools profile ad-blocks clarity / consent / otlp. Use clean Playwright Chromium with a real UA for that part.

## Baseline Google facts (written 21/10/2026, re-verify in step 0)
- Googlebot indexes the first **2MB** of each HTML file. CSS/JS are fetched separately, same cap.
- JS: non-200 pages may skip rendering. A `noindex` in the original HTML may skip rendering, so JS can't remove it. Canonical in raw HTML must equal rendered.
- `rel=canonical` is honoured only in `<head>`. Robots meta is honoured in `<body>` too.
- Faceted nav: for low-value filters prefer robots.txt disallow or fragments; canonical is weak long-term. Empty filter combos → 404.
- FAQ rich result is gone (May 2026). Search doesn't use `llms.txt` (Jun 2026). Breadcrumb rich result is desktop-only. New "back button hijacking" spam policy (Apr 2026).
- Merchant: org-level shipping + return policy markup is supported. `Product.category` and sale-price validity dates were added Jul 2026.

## 1 · Detect
Sample: home, PLP/category, PDP/post, static page, 1 filtered/sorted URL, `/robots.txt`, sitemap, 404 probe `/zz-404-<rand>`.
chrome-devtools MCP (default): `navigate_page` → `list_network_requests` + `get_network_request` (doc headers + raw body) → `evaluate_script`:
```js
() => { const q=s=>[...document.querySelectorAll(s)];
 return { url:location.href, shopify:window.Shopify?{shop:Shopify.shop,theme:Shopify.theme,root:Shopify.routes?.root,cur:Shopify.currency?.active}:null,
  next:window.next?.version||(window.__NEXT_DATA__?'pages':(self.__next_f?'app':null)),
  wp:!!q('link[href*="/wp-content/"],script[src*="/wp-content/"]').length, elementor:!!q('[data-elementor-type]').length,
  gen:q('meta[name=generator]').map(m=>m.content), wf:document.documentElement.dataset.wfSite||null,
  canon:q('link[rel=canonical]').map(l=>l.href+(l.closest('head')?'':' [BODY]')),
  robots:q('meta[name=robots],meta[name=googlebot]').map(m=>m.content),
  ld:q('script[type="application/ld+json"]').flatMap(s=>{try{const j=JSON.parse(s.textContent);return [].concat(j['@graph']||j).map(x=>x['@type'])}catch{return['INVALID']}}),
  h1:q('h1').length, links:q('a[href]').length, nodes:q('*').length, bytes:document.documentElement.outerHTML.length } }
```
Raw HTML: the doc response body, or `curl -sL -A '<Googlebot smartphone UA>'`. Cloudflare may block curl, so fall back to the browser.

| Layer | Signals |
|---|---|
| Shopify | `window.Shopify`, `cdn.shopify.com`, `/cdn/shop/`, `x-shopify-stage`, `powered-by: Shopify` |
| WordPress | `/wp-content/`, `Link: <…/wp-json/>; rel="https://api.w.org/"`, generator, Yoast / Rank Math HTML comments |
| Next / React | `__NEXT_DATA__` (Pages), `self.__next_f` (App), `/_next/`, `x-powered-by: Next.js`, `x-nextjs-cache`; empty `#root` = SPA |
| Builders | Framer generator / `framerusercontent.com`; Webflow `data-wf-site`; Wix `x-wix-request-id`; Squarespace `static1.squarespace.com` |
| Cache / CDN | `cf-ray`, `cf-cache-status`, `x-litespeed-cache`, `x-cache-status`, `x-varnish`, `x-vercel-cache`, `age` |
| Host | `x-vercel-id`, `platform: hostinger`, `server: nginx/LiteSpeed`, Cloudways Varnish, `x-nf-request-id` |

Record: theme + version, builder, **SEO owner** (who emits title / canonical / robots / JSON-LD, and duplicate count), cache layers, CDN/WAF, host, render mode (raw vs rendered parity), third parties (checkout, reviews, currency/geo, pixels, chat, deferral engines).

## 2 · Stack card
```
Platform: <name + version> · Theme/app: <name, id, version> · Builder: <…> · SEO owner: <plugin/app/theme/snippet>
Render: SSR|SSG|ISR|CSR|hybrid (raw-vs-rendered: title/canon/robots/H1/copy/links/JSON-LD = same|diff)
Cache/CDN: <layers, with the header seen> · Host: <…> · Third-party: checkout/reviews/currency/pixels/chat/deferral
Sampled: <URLs>
```

## 3 · Platform checklist
Load ONLY the matching ref(s): Shopify → `references/shopify.md` · WordPress (+Elementor/Woo) → `references/wordpress.md` · Next.js / React SPA → `references/nextjs.md` · Framer / Webflow / Wix / static / migrations → `references/other.md`.
Hybrid stacks (headless Shopify + Next, WP blog in a subfolder, a migration mid-flight) → load both.

## 4 · Cross-stack layer (always, cheap)
- **Host variants:** http/https × www/apex → one 301 hop to one host, with the same stack on every variant. (Seen: www still Framer while apex was WP.)
- **Platform/staging hosts** (`*.myshopify.com`, `*.vercel.app`, `*.hostingersite.com`, nip.io/sslip.io, `*.webflow.io`, `*.framer.app`): each should 301 or be noindexed. Prod must not carry staging noindex (check both meta and `X-Robots-Tag`).
- **CDN/WAF:** Googlebot UA gets 200, not a challenge. Check for a Cloudflare managed robots.txt block or AI-bot blocking at zone level (one zone can front many client hosts).
- **Cache truth:** `age` / `x-*cache*` headers decide whether the evidence is fresh. A fix may be live but still cached; note the bypass used.
- **Weight:** raw doc bytes vs the 2MB cap, DOM nodes, duplicated menus/sections.
- **Parity:** final URL == requested (watch for a client-side bounce to `/login`). Title, canonical, robots, H1, copy, `<a href>` links and JSON-LD should be the same raw and rendered.
- **Deferral engines** (`d-src`, `type="litespeed/javascript"`, `type="load"`, interaction-gated loaders): Lighthouse understates the cost, so use CrUX field data. Check whether pixels fire with no interaction.
- **Back-button hijack / forced-redirect scripts** (exit-offer apps) → spam-policy risk.
- **Cloaking:** diff Googlebot UA vs browser. IP cloaking can't be caught by UA; GSC URL Inspection is ground truth (`gsc_inspect_url` / `hub_gsc_inspect` if connected).

## 5 · Report
```
## Stack card  (§2)
## Findings
| # | Impact | Finding | Evidence (URL → observed) | Stack fix (file / setting / app) | Route |
## Hand-offs
Google Search updates checked (DD/MM/YYYY)
```
- **Impact:**
  - P0: deindex or site-wide (noindex, robots block, canonical → home, auth bounce, every route soft-404).
  - P1: template-wide duplication or crawl waste, broken sitemap, failing field CWV.
  - P2: one template or app.
  - P3: hygiene.
- **Route** (the owner executes, never this skill):
  - Shopify: pull LIVE by ID → edit locally → push to a non-live theme → client publishes.
  - WP: staging → PR → client cutover.
  - Next/React: PR-only (a merge to an auto-deploying main is a deploy).
  - No deploy without approval.
- **Hand-offs:**
  - Generic crawl/index/CWV/security headers → `seo-technical`
  - JSON-LD validity → `seo-schema`
  - hreflang matrix → `seo-hreflang`
  - Sitemap gaps → `seo-sitemap`
  - Product/merchant → `seo-ecommerce`
  - Full crawl + deck → `audit-site`
  - Hack, cloaking, spam pages indexed → `site-incident`; framework CVE / code review → `security-audit`
- **Output:** chat by default. When called from `audit-site`, write `<output_dir>/02b-tech-stack.md`.
