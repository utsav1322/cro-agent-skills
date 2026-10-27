# Shopify: platform checklist

## Detect / record
- **Store handle:** `Shopify.shop` is the permanent `*.myshopify.com` handle. It is often hashed (`e751f4-0b`, `31fb27-3`), so never guess it. The CLI needs the permanent domain; a vanity domain fails with a misleading "not authorized".
- **Theme:** `Shopify.theme` = {id, name, schema_name, schema_version, role}. Quote the **ID**: stores carry 15–20 near-identical "Copy of…" themes and the live ID moves under the same name.
- **Markets:** `Shopify.routes.root` (`/en-us/`…), `Shopify.country`, `Shopify.currency.active`, native `link[hreflang]`.
- **Apps:**
  - Sources: app embeds `cdn.shopify.com/extensions/…`, app proxies `/apps/…`, scripts in `content_for_header` (web-pixels-manager).
  - Inventory: checkout (GoKwik, FlexyPe, Shopflo, Shiprocket Fastrr), reviews (Judge.me, Loox, Yotpo, Okendo), currency/geo (Hextom-type, geolocation), SEO / JSON-LD apps, page builders (PageFly, GemPages, Shogun), speed/deferral apps, chat/WhatsApp, IG feeds / shoppable video.
- **Exact file needed?** Pull the live theme locally (`shopify theme pull -t <live-id> --path <proj>/_live-<date>`). That is read-only for the store. Then trace `{% render %}` from `layout/theme.liquid`.

## P0: indexability
- **Storefront password:** if it is on (redirect to `/password`, `layout/password.liquid` served), the whole store is blocked.
- **`templates/robots.txt.liquid` present?**
  - It REPLACES Shopify's generated file. Diff it against the default: it loses Shopify's future default changes (newer agent/AI lines were seen missing).
  - It must loop `robots.default_groups`. A syntax slip (stray `}`) breaks the rules.
  - Prefer the default unless there's a real need.
- **`/sitemap.xml`** must return XML 200, not a redirect. Seen: an app/redirect sent `/sitemap.xml` and `/products.json` to `/lander`. Check the child sitemaps (products, collections, pages, blogs) and the per-market sitemaps.
- **noindex sources:** theme head logic, SEO app, `seo.hidden` metafield (drops the resource from the sitemap). Confirm each hit is intentional per template.
- **Theme vs app owner:** if two places emit `<meta name=robots>` or a canonical, the app usually wins silently. Count the tags in the rendered `<head>`.

## P1: duplication / crawl waste
- **Product URL forms:** `/collections/x/products/y`, `/products/y?variant=`, market prefixes. Rendered canonical must be `/products/y` (Shopify default `canonical_url`). Hard-coded canonicals in the theme or an app break this; check the collection-scoped URL.
- **Internal links:** older themes use `| within: collection` in card links (`/collections/*/products/*`), which wastes crawl.
  - Fix: card link → `product.url`.
  - Files: `snippets/card-product.liquid` / `product-card*.liquid` / `product-grid-item.liquid`.
- **Facets / sort:** `filter.v.*`, `filter.p.*`, `sort_by`, tag pages `/collections/x/<tag>`, `+` tag combos.
  - Read the live robots.txt to see what's blocked by default (sort / `+` combos).
  - Decide filter crawling per Google's faceted doc: robots disallow beats canonical.
  - Shopify serves empty filter grids as 200 (can't 404) → block patterns crawled at scale (check GSC crawl stats).
- **Auto/thin pages:** `/collections/all`, `/collections/vendors?q=`, `/collections/types?q=`, `/blogs/*/tagged/*`, `/search`. Indexable? Linked from nav/footer?
- **Admin-side duplicates:** products with `handle-1` / `-copy`, and internal `[hidden]` collections that are publicly reachable and indexable. Their SEO field is set in admin, not the theme → hide/redirect/merge in admin.
- **Migration leftovers:** old WP `/product-category/`, `/wp-content/…`, `.html` URLs returning 404 → bulk-import into Admin URL Redirects.
  - Deleting a market subfolder needs its 301s imported (a 7k `/en-in/` set seen).
  - The bare subfolder root often needs its own redirect.
- **Markets / hreflang:**
  - Native for subfolders/domains. Verify reciprocity by rendering, don't assume missing.
  - Client-side currency apps (Hextom-type: rewrite `.money` spans, `/cart.js` stays in base currency) create no URLs and no hreflang. That's fine; don't "fix" it.
  - Geo auto-redirect apps must not bounce Googlebot (US IP / no cookie). Prefer a banner/selector.
  - **Two separate stores per country** (not Markets): cross-domain hreflang must be hand-built in BOTH themes and kept reciprocal.

## P1/P2: rendering and performance (theme + apps)
- **HTML weight vs 2MB:**
  - Header drawer/mega menu rendered twice (desktop + mobile), seen as ~300 duplicate links plus duplicate IDs.
  - Inline JSON blobs, inline SVG sprites, app markup.
- **LCP hero:** first-section image should be `loading="eager"` + `fetchpriority="high"`, via `image_url: width:` + srcset/sizes.
  - Not lazy, not a CSS background, not injected by slider JS.
  - Files: `sections/image-banner.liquid` / `slideshow.liquid` / `snippets/image*.liquid`.
- **App-injected media:**
  - Bare `cdn.shopify.com/s/files/…` URLs with no width param are full-res. Theme images go through `/cdn/shop/…&width=`.
  - Attribute bytes by DOM class, not by CDN host. Seen: an IG-feed app was 60MB of `<video>` on the homepage.
- **Render-blocking:** count the stylesheets (53 seen). Fix = merge into the existing stylesheet; never add a new brand CSS file.
- **Third-party checkout** bundles (GoKwik / FlexyPe / Shopflo / Fastrr) load site-wide → TBT/INP on every template.
- **Deferral hacks:**
  - Signs: `d-src` / `d-href` rewrites, `type="load"`, `trekkie` / `BOOMR` stubs, MutationObserver blocklists (e.g. blocking `wpmLoader`).
  - Effect: Lighthouse sees nothing and pixels wait for interaction.
  - Use CrUX field data plus an interaction trace. Propose targeted carve-outs; removing the hack is the owner's call.
- **Static check:** `shopify theme check` on the pull (OrphanedSnippet, missing assets, Liquid errors).

## P2: structured data ownership (validity → seo-schema)
- **Duplicates:** count rendered JSON-LD `@type`s. Sources: theme `product | structured_data` + review app + SEO app + custom snippet → duplicate Product / Organization / Breadcrumb. One owner.
- **Filter limits:** `| structured_data` can't emit `shippingDetails` / `hasMerchantReturnPolicy`. Use a custom Product snippet, or org-level shipping/return markup, or Merchant Center policies.
- **Find the RENDERED snippet.** Retired copies with authoritative names linger; one store burned 3 rounds editing the wrong file. Verify by rendering, never by grep.
- **Alternate templates:** `product.<suffix>.json` / `collection.<suffix>.json`. A section added only to `product.json` misses those products → list `templates/product.*.json`.
- **FAQPage** (apps/sections): no Google rich result since May 2026. Keep only for on-page/GEO value.
- **Reviews:** never import cross-platform reviews (Etsy, marketplace) into product `aggregateRating`. Rating blocks must guard empty/0 counts.
- **`/llms.txt`** is a native Shopify system route (can't override; a custom map lives at `/pages/llms-txt` via `templates/page.llms.liquid`). Google Search doesn't use it.

## Verify (cache traps)
- Storefront HTML stays cached for minutes after a push. Verify via the Section Rendering API (`?section_id=<id>`) or `?preview_theme_id=<id>`. Never call a fix failed from a cached fetch.
- Development-theme preview links only render in a browser logged into admin.

## Fix workflow (proposal; the owner executes)
1. `shopify theme list --store <permanent>.myshopify.com` → match LIVE **by ID** → `theme pull -t <live-id>` → edit locally → diff.
2. Push only to a non-live theme: `-t <unpublished-id> --nodelete --only <files>`.
   - Push sections/assets first, then `templates/*.json` ALONE (a same-batch push prunes new settings).
   - Never do a bare full push: it clobbers `settings_data.json` and admin edits.
3. **Never `--unpublished`:** it PUBLISHED the new theme on a client store. After any push, run `theme list` and confirm `[live]` is unchanged.
4. **20-theme cap:** `--unpublished` fails. `--development` doesn't count toward the cap (docs) but only previews for admin-logged browsers and is deleted after 7 days idle or on `auth logout`. Never delete client themes; ask the owner which copy can go.
5. `--allow-live` only with explicit approval. Never `shopify auth logout` to probe identity.
6. **Tracking/app tags:** app embed first. In `config/settings_data.json`, find `blocks[*].type` = `shopify://apps/…` and confirm `disabled:false` before removing any theme snippet.
7. **Admin-only fixes** (not theme): URL redirects, product/collection SEO fields, `seo.hidden`, Markets/domains, app settings. Checkout "additional scripts" are deprecated → checkout UI extension.
8. **Naming:** new code uses neutral names (`snippets/seo-head.liquid`, `snippets/product-jsonld.liquid`). Currency-app-safe prices: `<span class="money">`.

## Don't misdiagnose
- On GoKwik / FlexyPe / Shopflo stores, Shopify's conversion tile and funnel are wrong (orders carry no sales channel; no post-ATC pixel events). That's analytics, not SEO; hand it off.
- Hand-offs: schema → `seo-schema` · merchant/Product → `seo-ecommerce` · hreflang matrix → `seo-hreflang` · images → `seo-images`.
