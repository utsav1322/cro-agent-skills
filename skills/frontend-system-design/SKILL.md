---
name: frontend-system-design
description: Front-end architecture + UI-component design reference. Auto-invoke (no slash) BEFORE designing or building any non-trivial React/Next.js component, widget, or full client-side app feature — e.g. cart/checkout, autocomplete, carousel, modal, infinite-feed, data-table, design-system component, offline-sync, server-driven UI, i18n, real-time/collab UI. Trigger on intent like "build a cart", "design the checkout UI", "autocomplete component", "infinite scroll feed", "build a carousel", "data table with sort/filter", "real-time/collab feature", "offline sync", "design system component", or any prompt that means architecting front-end state/data-flow/rendering for a complex UI. Pulls battle-tested patterns (state shape, data flow, API design, rendering strategy, accessibility, perf, edge cases) from the curated greatfrontend/awesome-front-end-system-design corpus on disk. SKIP for WordPress theme/Liquid/plain-HTML work and for trivial one-element edits. Reference-only — informs the design, does not write app code by itself.
metadata:
  type: reference
---

# frontend-system-design — auto-loaded FE architecture reference

Curated corpus: greatfrontend/awesome-front-end-system-design, cloned at
`~/.claude/skills/external/awesome-front-end-system-design/` (pin `f56c0f3`, MIT).
Single source file: `README.md` (~40KB) + `assets/`.

## When this fires (automatic, no slash command)

Invoke yourself BEFORE writing code for any **non-trivial React/Next.js front-end**:

- Full-app features: cart, checkout, news/infinite feed, chat, product grid, dashboard, collaborative editor, video/media UI
- UI components: autocomplete/typeahead, carousel, modal/dialog, dropdown/menu, tooltip, data-table (sort/filter/paginate), image gallery, design-system primitives
- Techniques: offline-sync, server-driven UI, i18n, optimistic updates, real-time, AI-integration UI

**SKIP** for: WordPress themes/plugins, Liquid sections, plain HTML/CSS pages, SEO work, or a one-line/one-element tweak. Those gain nothing here.

## What to do when it fires

1. Read the relevant section of `~/.claude/skills/external/awesome-front-end-system-design/README.md`
   (sections: General · Applications · Techniques/Topics · User Interface Components · Miscellaneous).
   Grep for the matching pattern, e.g. `grep -i -A3 "autocomplete\|e-commerce\|data table" README.md`.
2. Extract the design checklist that corpus implies for this component/app:
   - **State shape** — what state, where it lives, normalize vs nested
   - **Data flow** — fetch strategy (SSR/CSR/streaming), caching, optimistic vs pessimistic
   - **API surface** — endpoints/shape the UI needs; pagination/cursor; error contract
   - **Rendering** — virtualization for long lists, lazy/suspense boundaries, skeleton states
   - **Accessibility** — keyboard nav, ARIA roles, focus management (esp. modal/menu/autocomplete)
   - **Performance** — debounce/throttle, memoization, bundle split, image strategy
   - **Edge cases** — empty/loading/error/offline, race conditions, stale data, concurrency
3. Feed that checklist into the design BEFORE coding. Surface the 3-5 decisions the user must make.
4. If pairing with superpowers `brainstorming`/`writing-plans`, this supplies the FE-architecture
   content for the spec; superpowers owns the loop. Don't duplicate the spec ceremony.

## Boundaries

- Reference-only. Does NOT write app code by itself — informs the plan, then normal build proceeds.
- Honor locked the agency rules in any code that follows: Lucide-only icons, IST date format,
  commits without AI attribution.
- Corpus is a link-list to external eng blogs; for deep dives the README points at source URLs —
  fetch those only when the on-disk summary is insufficient.
