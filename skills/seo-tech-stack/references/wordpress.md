# WordPress (+Elementor / WooCommerce): platform checklist

## Detect / record
- **WP signals:** `/wp-content/`, `/wp-includes/`, header `Link: <…/wp-json/>; rel="https://api.w.org/"`, `/wp-json/` 200, generator meta (security plugins often strip it, along with `?ver`).
- **Theme:** `/wp-content/themes/<slug>/` (child + parent).
- **SEO owner:** HTML comments from Yoast / Rank Math / AIOSEO / SEOPress, or a custom/fleet SEO + schema plugin.
  - For a custom plugin, read its live `Version:` header. A site stuck on an alpha/beta header never auto-updates, so a fix in the repo may not be live.
- **Builder:**
  - Elementor: `data-elementor-type`, `/plugins/elementor/`, Pro, containers `e-con` vs legacy `elementor-section`.
  - Others: Divi `et_pb_`, WPBakery `vc_`, Gutenberg/FSE `wp-block-`.
- **Woo:** `woocommerce` body class, `/wc/store/v1/` requests, `wc-blocks`.
- **Cache layers seen:**
  - `x-litespeed-cache` (Hostinger: `platform: hostinger`).
  - `x-cache-status` (nginx `proxy_cache`, CloudPanel / VPS).
  - `x-varnish` / `via` (Cloudways + Breeze).
  - WP Rocket / W3TC footer comments.
  - `cf-cache-status`, `cf-apo-via` (Cloudflare APO).
- **Security plugin:** Wordfence / AIOWPS / agency plugin. Known behaviours: strips `?ver`, blocks `/author/`, renames the admin URL (`/wp-admin/` 404 is normal).
- **SSH/WP-CLI** (only if the project allows it, read-only): `wp option get blog_public`, `wp plugin list`, `wp rewrite list`, `wp option get permalink_structure`.

## P0: indexability
- **"Discourage search engines" (`blog_public=0`):** core prints `noindex, nofollow` AND disables ALL core sitemaps (`/wp-sitemap.xml` 404). Two failure modes:
  - Prod cloned from staging keeps `0`.
  - Staging (`*.hostingersite.com`, nip.io / sslip.io, `staging.`) left indexable.
  - Also check a vhost-level `X-Robots-Tag`.
- **SEO-plugin global noindex** on a post type or taxonomy (products, posts, categories) → check one URL per type.
- **Hacked / cloaked:**
  - Googlebot-UA HTML ≠ browser HTML (gambling / Japanese spam served to bots via a replaced root `index.php`).
  - Rogue admins, GSC Security Issues.
  - Hand to `site-incident`, then GSC review. UA diff misses IP cloaking → use URL Inspection.
- **robots.txt:**
  - Physical file vs WP virtual vs plugin-edited.
  - Staging `Disallow: /` copied to prod.
  - A Cloudflare-managed block prepended at the edge.
- **Virtual routes outside posts** (rewrite rules + a custom table, e.g. pSEO condition/location pages):
  - `wp post list` shows nothing, and the "status" field isn't a WP status (`active` / `unlist` / `draft`).
  - The SEO plugin may emit the wrong title / canonical / noindex (treats the route as home or 404) and leave it out of the sitemap.
  - Check each virtual template's head and sitemap inclusion.

## P1: duplication / crawl waste
- **Sitemaps:**
  - Exactly ONE live system: core `/wp-sitemap.xml` OR the plugin's `/sitemap_index.xml`, and robots `Sitemap:` points to it.
  - It lists no noindexed or redirecting URLs, and no builder/library CPTs (`elementor_library`, header/footer template CPTs).
- **Attachment pages:** WP ≥6.4 new installs disable them (`wp_attachment_pages_enabled`=0). Older sites have them on → thin `?attachment_id=` / `/<post>/<image>/` pages → SEO plugin "redirect attachments" toggle.
- **Archives:**
  - Tag / date / format archives, `/page/N/`, internal search `?s=` (spam-query injection target) → noindex via SEO plugin settings.
  - Author archives: if a security plugin 301s `/author/` → home, never point Person schema `url` or links at them. On a single-author blog the author archive duplicates the blog.
- **Permalinks:** plain `?p=`, `/index.php/` prefix, inconsistent trailing slash, uppercase, category-base duplicates.
- **Woo params:**
  - `?orderby=`, `?filter_*`, `?min_price=`/`max_price`, `?query_type_*`, `?attribute_pa_*` → robots/canonical per Google's faceted doc.
  - `?add-to-cart=` links are crawlable, burn crawl and bypass cache → robots `Disallow: /*add-to-cart=*`.
  - Cart / checkout / my-account must be noindex (Woo default; verify).
  - Out-of-stock: keep 200; discontinued → 301 to the closest category.
- **Staging → live leakage:**
  - Staging host strings left in canonical / OG / JSON-LD / sitemap after a clone (incomplete search-replace).
  - Cutover moves FILES not DB: page `post_content`/meta can differ between installs (a page frozen on old static HTML on live was seen).

## P1/P2: cache truth ("my fix didn't apply")
- **Layers, inner → outer:**
  1. OPcache (`validate_timestamps=0` → php-fpm reload)
  2. Object cache (Redis)
  3. Elementor element cache (`e_element_cache`: stale widget HTML, bypasses render filters)
  4. Page-cache plugin (LiteSpeed Cache / WP Rocket / W3TC / Breeze)
  5. Server cache (LiteSpeed server, nginx `proxy_cache`; `wp cache flush` does NOT clear it)
  6. CDN (Cloudflare / APO)
- Purge inner → outer. Report which layer served the evidence (headers) and how it was bypassed.
- **Custom routes / non-post pages** aren't purged by `save_post` → index pages stay stale (plugin-specific purge needed).
- **`?ver` stripped by a security plugin + 7-day `max-age`:** CSS/JS never refresh. Fix: enqueue with `add_query_arg('v', filemtime($path), $url)`, not `$ver`.
- **LiteSpeed Guest Mode:** the first cookieless hit gets a 307 to `?v=<hash>`. It's server-level; plugin toggles don't remove it; fix in hPanel or via host support. Bots see a redirect plus param duplicates → test the first request with no cookies.
- **LiteSpeed "Load JS Deferred" / WP Rocket "Delay JS":** scripts run on interaction, so lab metrics lie. Critical inline JS needs `data-no-optimize="1"` or an exclusion.

## P2: rendering / performance
- **Elementor:**
  - DOM depth (legacy section > column > widget → Flexbox Containers).
  - Per-post CSS `uploads/elementor/css/post-N.css`.
  - Google Fonts + Font Awesome / eicons loaded globally (Settings → Performance / Features: local fonts, inline icons, improved asset loading).
  - "Hide on mobile/desktop" keeps BOTH copies in the DOM → duplicate content + weight.
  - Hero as a CSS background isn't preloadable → LCP.
  - Heading widget tags: multiple H1s, site title as H1 globally.
- **Plugin assets on every page** (sliders, forms, Woo scripts on non-shop pages) → conditional dequeue in the theme.
- **Huge `wp_users`** (every customer is a user, 200k+): role/author-shaped queries (`count_users`, `who=authors`, author dropdowns) scan the whole table.
  - Symptom: slow admin/editor; not an SEO issue by itself.
  - SEO check: TTFB on `/author/*` and users sitemaps. EXPLAIN before blaming plugins.

## P2: structured data ownership (validity → seo-schema)
- **One emitter per type:** SEO plugin graph vs theme JSON-LD vs Woo vs review plugin vs schema plugin (a double Product block was seen). Disable the extra emitter at its source.
- **Fleet/shared plugins** that must stay byte-identical: extend via their filter hooks from the theme, never edit the plugin.
- **Term names** are stored with `&amp;` → decode before JSON-LD and look terms up by slug.

## Fix workflow (proposal; the owner executes)
- **Path:** staging clone → verify (headless) → PR → client "cut over" → backup → deploy → purge inner → outer → smoke test.
- Deploy theme changes to BOTH installs if staging and live are separate.
- **No git on the server:** `cp -p` backup before any change, then `php -l`.
- **Change the existing owner:** a setting in the SEO plugin beats theme code. Never add a second emitter.
- **Admin-path fixes:** list the exact screen (Settings → Reading; Yoast → Settings → Advanced → Crawl optimization / Media; Rank Math → Titles & Meta; Elementor → Settings → Performance / Features).
- **New code naming:** theme-prefixed (`<theme>_seo_*`), no agency prefix. PR-only repos per project.

## Hand-off
- Schema → `seo-schema` · CWV deep dive → `seo-technical` · sitemap diff → `seo-sitemap` · hack / cloaking → `site-incident`.
