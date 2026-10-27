---
name: shopify-ui-audit
description: 'Read-only Shopify UI design audit before redesign: hierarchy, typography, spacing, buttons, breakpoints, accessibility, theme editor settings, and visual regression. Use for Shopify UI audit, design consistency, or redesign review.'
---

# Shopify UI audit

Audit first, propose changes second, and edit only after explicit approval. This skill reviews a Shopify storefront design, not conversion performance; route behavioral funnel claims to `ecom-cro` and technical SEO to `seo-tech-stack`.

## Inputs and evidence

- Identify the client, URL, desktop/mobile page templates, theme and theme version when available.
- Read the project's local context before examining theme files. Preserve client ownership and confidentiality.
- Inspect homepage, a collection, a product page, cart, and any special landing page in scope.
- Record screenshots at representative mobile and desktop widths, observed CSS/DOM evidence, and affected selectors/files where accessible. Mark any inaccessible pages or settings as unverified.
- Read-only mode: do not edit, push, publish, place orders, or toggle apps during an audit.

## Checklist

1. Hierarchy: primary heading, price, variant, product CTA, supporting content, and disclosure order.
2. Typography: font families, scale, weights, line heights, readability, text zoom, and wrapping.
3. Spacing and layout: page rhythm, component spacing, responsive containers, content density, sticky overlays, and safe areas.
4. Components: buttons, form inputs, radii, colors, focus/hover/disabled states, consistent tokens.
5. Accessibility: keyboard navigation, visible focus, contrast, labels, error messages, reduced motion, and touch targets.
6. Shopify behavior: theme editor settings and section/block schemas, product forms, variant updates, cart events, app embeds, checkout integration, locale/currency/Markets, tracking pixels.
7. Performance: CLS risks, image dimensions, font loading, and interaction delays; use field data before claiming a measurable improvement.

## Required report

For each issue provide: page URL/template, observed evidence, screenshot or file/selector reference, severity, proposed change, scope and risks, confidence, and how to verify it. Distinguish observed defects from aesthetic preferences. Provide a five-item prioritized proposal before implementation.

## Approval and implementation

- Ask for explicit approval of the individual proposed changes.
- On approval, apply only to a local working copy or non-live development theme.
- Preserve schema compatibility and app integrations. Compare mobile and desktop screenshots before and after.
- Run available lint/Theme Check, accessibility checks, product and cart smoke tests, and browser console checks.
- Summarize verified results and remaining risks; publish only upon separate explicit approval.
