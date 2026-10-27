# Other stacks: Framer / Webflow / Wix / Squarespace / static / migrations

## Detect / record
- **Framer:** generator `Framer <ver>`, `framerusercontent.com` assets, `events.framer.com`. Staging `*.framer.app` / `*.framer.website`.
- **Webflow:** `<html data-wf-site data-wf-page>`, `cdn.prod.website-files.com` / `assets.website-files.com`, generator Webflow. Staging `*.webflow.io`.
- **Wix:** generator "Wix.com Website Builder", `static.wixstatic.com`, `x-wix-request-id`, `*.wixsite.com`.
- **Squarespace:** `static1.squarespace.com`, Squarespace in generator/server.
- **Ghost:** generator Ghost, `/ghost/api/`.
- **Hostinger Website Builder:** zyrosite-hosted assets (confirm via generator).
- **Static:**
  - No generator; identify by host headers: Netlify (`server: Netlify`, `x-nf-request-id`), GitHub Pages (`server: GitHub.com`), Cloudflare Pages (`*.pages.dev`), S3/CloudFront (`x-amz-cf-id`).
  - Shared Apache/LiteSpeed: `.htaccess` rewrites.
- **Mixed hosts:** www vs apex, or a subfolder, served by DIFFERENT stacks (seen: www still on Framer after apex moved to WP; a WP `/blog` reverse-proxied under Shopify/Next). Record each.

## Builder limits: say what can't be fixed in-platform (don't promise it)
- **Headers:** usually no server-header / `X-Robots-Tag` control. noindex is page-level only, and non-HTML files (PDFs) can't be noindexed → remove them or block in robots.
- **Canonical:** per-page field, plus a global canonical setting (Webflow "Global canonical tag URL") and CMS-template canonicals. Arbitrary per-URL control is limited.
  - Custom head code is site-wide → never hard-code a page-specific canonical / robots / hreflang there.
- **hreflang:** use native localization (Framer Locales, Webflow Localization, Wix Multilingual). Hand-coded hreflang must be reciprocal on every page.
- **robots.txt:** usually editable on paid plans; confirm what's actually served.
- **Sitemap:** auto-generated. Exclusions via per-page "exclude from sitemap" / noindex. CMS collection items are included by default, thin ones too.
- **Redirects:** built-in 301 tables (Webflow hosting settings, Framer redirects, Wix redirect manager). Pattern/regex support varies → plan big migration maps.
- **JS weight:** the platform runtime (Framer hydration, Webflow IX2 + jQuery, Wix) bounds CWV. Fix what's controllable: hero image size/format, fonts, embeds, third-party scripts.

## P0: indexability
- **Staging/builder subdomain indexed?**
  - Webflow: "Disable Webflow subdomain indexing".
  - Others: confirm a 301 to the custom domain or a noindex. `site:` check + GSC.
- **Host variants:** every variant resolves to ONE stack and 301s to one canonical host. An old-platform host left live = a duplicate site.
- **Leftover build toggles:** site-wide password / "hide from search engines" / noindex left on from the build.
- **Global custom-code injection:** a canonical, noindex or base tag on every page from one head snippet.

## P1: duplication / crawl
- **CMS:** template pages with titles/meta auto-filled from the item name (duplicates), empty/placeholder items, Webflow pagination `?<hash>_page=2` params.
- **URL forms:** trailing slash, uppercase, `/index`, `.html` vs extensionless vs `/dir/`. Each should canonicalise + 301 to one form.
- **Static sites:**
  - `.htaccess` / host rewrites that serve a different file as index (e.g. `preview.html` → `/`) → check status + canonical of every reachable form.
  - Hand-made sitemap stale (`lastmod`, missing pages); robots missing the `Sitemap:` line.
  - Purge host/LiteSpeed/CDN cache after a deploy before verifying.
- **Migrations (any → any)**, e.g. Shopify → Next, WP → Shopify, Framer → WP, JS one-pager → WP:
  - Old URL patterns (`/product-category/`, `/wp-content/uploads/`, `/products/` `/collections/`, `.html`) → 404s.
  - Build a 1:1 map from the old sitemap + GSC pages + backlinked URLs. Use 301, not 302 / meta-refresh / JS. Redirect images/PDFs too.
  - After cutover: submit the new sitemap, and keep the old host/property in GSC to watch 404s.

## P2: rendering / weight / schema
- **Embeds** (Calendly, IG feeds, autoplay video, chat) often dominate weight → facade / lazy / click-to-load.
- **Builders inject little or no JSON-LD.** Organization/WebSite can live in the global head. Product / Article / LocalBusiness belong at page/CMS-template level, never duplicated site-wide.
- **Framer/Webflow images:** check the LCP image is not lazy and has proper srcset (framerusercontent / website-files URLs carry width params).

## Fix workflow (proposal; the owner executes)
- **Builder setting changes** are client-account actions → give the exact path (Site settings → SEO / Publishing / Hosting / Redirects / Localization). Read-only here.
- **Static repos:** PR-only; note the cache purge needed after deploy.
- **Migration redirects:** deliver as a CSV in the target platform's importer format (Shopify URL Redirects, Webflow 301s, `.htaccess`, `next.config` `redirects`).
- **Naming:** new custom-code snippets and IDs stay neutral.

## Hand-off
- Redirect-map validation / crawl → `audit-site` · schema → `seo-schema` · hreflang → `seo-hreflang` · CWV → `seo-technical`.
