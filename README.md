# CRO Agent Skills

A public library of <!-- OWN-COUNT -->32<!-- /OWN-COUNT --> Claude Code **skills** for agency and product work — development, planning, SEO, security, data, and legal/compliance research — plus a curated index of the third-party skills and plugins they pair with.

Skills are model-invoked: once installed, Claude Code reads each skill's description and fires the right one automatically when your request matches. You don't type a slash command.

**Does it work in every AI tool?** Partly. `SKILL.md` is Anthropic's Agent Skills format, so these are **native and auto-invoked in Claude Code and the Claude apps**. Other agents (Codex, Cursor, etc.) don't auto-discover or auto-fire them — but every skill is plain Markdown plus optional `references/` and `scripts/`, so you can read it, paste the relevant `SKILL.md` into any model, or point any agent at the file manually. The bundled scripts run anywhere. Short version: **auto in Claude, usable-as-content everywhere else.** See [AGENTS.md](AGENTS.md) for how non-Claude agents should use these.

## Install

Copy any skill folder into your Claude Code skills directory:

```bash
# all of them
cp -R skills/* ~/.claude/skills/

# or just one
cp -R skills/seo-tech-stack ~/.claude/skills/
```

Restart Claude Code (or start a new session) so it picks up the new skills. Some skills bundle `references/`, `scripts/`, or `templates/` — keep the whole folder together.

## Skills

<!-- OWN-SKILLS:START -->
### Project & workflow

| Skill | What it does |
|---|---|
| [`project-start`](skills/project-start/SKILL.md) | Start, resume or switch to a named project using minimum required context when the user says work on, resume, continue, open, switch to or check a project. |
| [`task-dispatch`](skills/task-dispatch/SKILL.md) | Decide whether a task requires direct work, one specialised capability, or high-complexity planning and independent reviews. |
| [`capability-intake`](skills/capability-intake/SKILL.md) | Study one newly installed skill, MCP server, plugin, agent pack, hook, integration or tool and document only behaviour required for actual workflows. |
| [`context-audit`](skills/context-audit/SKILL.md) | Audit Claude Code configuration for oversized startup context, unnecessary imports, duplicated rules, duplicated workflows and incorrectly loaded capability information. |
| [`setup-project-context`](skills/setup-project-context/SKILL.md) | Create, migrate or audit a project's docs to the numbered docs/01–17 standard (lean CLAUDE.md index + slots). Use for new projects, for restructuring legacy docs… |
| [`update-md`](skills/update-md/SKILL.md) | Update project Markdown documentation from actual progress when the user says update md, update docs, save progress, update tasks, update context, update project md… |
| [`build-review-loop`](skills/build-review-loop/SKILL.md) | Default build-and-review loop for any real coding request typed in the composer — writing, editing, refactoring or fixing application code, components, endpoints… |
| [`llm-council`](skills/llm-council/SKILL.md) | Run any question, idea, or decision through a council of 5 AI advisors who independently analyze it, peer-review each other anonymously, and synthesize a final verdict —… |

### Development & architecture

| Skill | What it does |
|---|---|
| [`dev-agents`](skills/dev-agents/SKILL.md) | Multi-part dev work with subagents — sizing gate, roles, contracts-first parallel build, worktrees, briefs, review/verify. Use for "build end to end", "big feature"… |
| [`dev-patterns`](skills/dev-patterns/SKILL.md) | House build patterns - auth/roles, payments (Razorpay/Stripe), webhooks, cron/jobs, file uploads, email/WhatsApp, audit log, multi-currency, API errors, LLM features.… |
| [`backend-architecture`](skills/backend-architecture/SKILL.md) | Backend architecture decisions mid-project: how should we architect, ERP/OMS sync, order sync, webhook reliability, idempotency, data model, ADR, scale this. Smallest… |
| [`frontend-system-design`](skills/frontend-system-design/SKILL.md) | Front-end architecture + UI-component design reference. Auto-invoke (no slash) BEFORE designing or building any non-trivial React/Next.js component, widget, or full… |
| [`technical-feasibility`](skills/technical-feasibility/SKILL.md) | Check whether a feature can be built: platform and API limits, scopes, access, legal blockers, smallest viable build, alternatives. Use for "is this possible", "can… |
| [`rea-research`](skills/rea-research/SKILL.md) | Evaluate REA for authorized reverse engineering of binaries, Electron apps, closed-source JavaScript, Android packages or observed runtime behavior. Use for… |

### Planning & delivery

| Skill | What it does |
|---|---|
| [`idea-validator`](skills/idea-validator/SKILL.md) | Stress-test a new business, product or SaaS idea: users, pain, competitors, cost, distribution, riskiest assumption, cheapest validation experiment. Use for "validate… |
| [`requirements-business-analyst`](skills/requirements-business-analyst/SKILL.md) | Turn a client brief, call notes or RFP into traced requirements: functional and non-functional, ambiguities, dependencies, acceptance criteria, clarification log. Use… |
| [`project-estimation-planning`](skills/project-estimation-planning/SKILL.md) | Estimate effort and schedule for a dev or SEO project: task breakdown, client inputs, QA and release buffer, assumptions, confidence range, kept separate from contract… |
| [`competitor-market-analysis`](skills/competitor-market-analysis/SKILL.md) | Dated competitor and market comparison: direct rivals vs substitutes, cited features and prices, positioning gaps. Use for "competitor analysis", "who else does this"… |
| [`tech-research-intelligence`](skills/tech-research-intelligence/SKILL.md) | Research fast-changing frameworks, AI tools and platforms from primary docs and dated release notes: stable vs preview vs deprecated, licences, pricing, lock-in, small… |
| [`sop-process-builder`](skills/sop-process-builder/SKILL.md) | Write repeatable SOPs and checklists for the team: trigger, owner, inputs, permissions, exact steps, exceptions, proof of done, escalation, rollback, version. Use for… |

### SEO & ecommerce

| Skill | What it does |
|---|---|
| [`seo-tech-stack`](skills/seo-tech-stack/SKILL.md) | Detect site stack (Shopify, WordPress/Elementor/Woo, Next.js, Framer/Webflow) from the live page; run stack-specific tech-SEO checks + fixes. Use for "what is this site… |
| [`shopify-ui-audit`](skills/shopify-ui-audit/SKILL.md) | Read-only Shopify UI design audit before redesign: hierarchy, typography, spacing, buttons, breakpoints, accessibility, theme editor settings, and visual regression. Use… |
| [`make-slides`](skills/make-slides/SKILL.md) | Turn any markdown file into a slide deck (PDF + PPTX + HTML) using Slidev. Trigger on natural-language phrases like "turn this into slides", "make a deck", "slide deck"… |

### Security & data

| Skill | What it does |
|---|---|
| [`secrets-credential-manager`](skills/secrets-credential-manager/SKILL.md) | Keep secrets out of chat, code, docs and git: managed storage, environment separation, leak scans of diffs and history without copying values, rotation and revocation.… |
| [`password-authentication-security`](skills/password-authentication-security/SKILL.md) | Audit login and password flows without handling real passwords: policy, breached-password checks, Argon2id or bcrypt hashing, MFA, rate limits, lockout, reset and… |
| [`data-privacy-security`](skills/data-privacy-security/SKILL.md) | Engineer personal-data protection in an app: PII inventory and flows, encryption in transit and at rest, key access, retention and deletion, anonymised logs, tenant… |
| [`data-analysis-insights`](skills/data-analysis-insights/SKILL.md) | Analyse business, conversion or product data from CSV, sheets or exports: schema and null checks, defined denominators, segments, correlation vs causation, reproducible… |
| [`site-incident`](skills/site-incident/SKILL.md) | Hacked WordPress site or compromised VPS playbook — triage, read-only evidence, contain, clean-vs-rebuild, harden, verify, client comms, post-mortem. Use for "site… |

### Legal & compliance (research support, not legal advice)

| Skill | What it does |
|---|---|
| [`international-legal-research`](skills/international-legal-research/SKILL.md) | Cross-border legal research for foreign clients (GDPR, UK GDPR, US state laws, UAE): jurisdictions, data locations, controller vs processor, transfers, cited primary… |
| [`privacy-data-protection-law`](skills/privacy-data-protection-law/SKILL.md) | Privacy-law assessment for a site or app: personal data map, DPDP vs GDPR and local regimes with commencement dates, lawful basis, notices, retention, rights, transfers.… |
| [`intellectual-property-licensing`](skills/intellectual-property-licensing/SKILL.md) | Check software and asset rights: OSS dependency licences (SPDX), redistribution duties, commissioned-work ownership, images, fonts, trademarks, brand permissions, before… |
| [`legal-document-drafter`](skills/legal-document-drafter/SKILL.md) | Draft working copies of legal documents (privacy policy, terms, refund policy, NDA, service agreement) from verified jurisdiction facts, with placeholders and a… |
<!-- OWN-SKILLS:END -->

## Third-party skills & plugins

These are **listed, not vendored** — fetch each from its own upstream. `scripts/update-third-party.sh` re-pulls them to the latest version and records the resolved commit/version in `third-party-sources.json`; the weekly drift workflow reports when an upstream has moved.

<!-- THIRD-PARTY:START -->
| Source | Skills / plugins | Fetch |
|---|---|---|
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | `cro`, `ab-testing`, `conversion-tracking`, `analytics`, `copywriting`, `popups`, `ads`, `ad-creative`, `social`, `link-building`, `community-marketing`, `attribution` | `npx -y skills add coreyhaines31/marketingskills -g -a claude-code --copy -y -s <skills>` |
| [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | `wordpress-router`, `wp-project-triage`, `wp-plugin-development`, `wp-rest-api`, `wp-performance`, `wp-wpcli-and-ops` | `npx -y skills add WordPress/agent-skills -g -a claude-code --copy -y -s <skills>` |
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | `*` | `npx -y skills add AgriciDaniel/claude-seo -g -a claude-code --copy -y` |
| [Shopify/liquid-skills](https://github.com/Shopify/liquid-skills) | `liquid-theme-a11y` | `npx -y skills add Shopify/liquid-skills -g -a claude-code --copy -y -s liquid-theme-a11y` |
| [trailofbits/skills](https://github.com/trailofbits/skills) | `supply-chain-risk-auditor` | `npx -y skills add trailofbits/skills -g -a claude-code --copy -y -s supply-chain-risk-auditor` |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `tdd` | `npx -y skills add mattpocock/skills -g -a claude-code --copy -y -s tdd` |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | `last30days` | `npx -y skills add mvanhorn/last30days-skill -g -a claude-code --copy -y -s last30days` |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | `apple-design`, `emil-design-eng`, `animate`, `improve-animations`, `review-animations`, `animation-performance`, `mobile-native`, `break-ui`, `prototype` | `npx -y skills add emilkowalski/skills -g -a claude-code --copy -y -s <skills>` |
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) (pinned) | `geo-audit`, `geo-citability`, `geo-crawlers`, `geo-llmstxt`, `geo-platform-optimizer` | hand-copy at pinned commit |
| [garrytan/gstack](https://github.com/garrytan/gstack) | `gstack` | self-updating (gstack-upgrade) |

**Plugins** (install from their marketplace, keep current with the update command):

| Plugin | Update |
|---|---|
| `caveman@caveman` | `claude plugin update caveman@caveman --scope user` |
| `cloudflare@cloudflare` | `claude plugin update cloudflare@cloudflare --scope user` |
| `higgsfield@higgsfield` | `claude plugin update higgsfield@higgsfield --scope user` |
| `shopify-ai-toolkit@claude-plugins-official` | `claude plugin update shopify-ai-toolkit@claude-plugins-official --scope user` |
| `liquid-lsp@claude-plugins-official` | `claude plugin update liquid-lsp@claude-plugins-official --scope user` |
<!-- THIRD-PARTY:END -->

## Tracked good repos

Beyond the skills in this repo, we keep a running, opinionated library of Claude Code skill/plugin/tool repos worth knowing about — each with a verdict (**Adopted / Subset / Watching / Parked / Skipped**) and the reason, plus a terse-output comparison and a positioning table vs other skill libraries. It's reviewed on the 1st of each month (a scheduled workflow opens a reminder issue).

→ **[GOOD-REPOS.md](GOOD-REPOS.md)** — the full library, comparison, and review log.

## Keeping it current

- **Third-party:** `scripts/update-third-party.sh --check` reports drift; without `--check` it re-pulls and bumps the pins. Needs `gh`, `npx`, `python3`, and the Claude binary for plugins.
- **Own skills:** maintained in a private source-of-truth workspace and mirrored here by `scripts/sync-from-private.sh`, which scrubs internal references and runs a leak gate before writing — nothing that fails the gate is published. 27 fully-generic skills auto-sync from the private source each run; the other 5 (`dev-agents`, `dev-patterns`, `make-slides`, `setup-project-context`, `site-incident`) are hand-cleaned and edited directly here, so the sync never overwrites them.

## Repo layout

```
skills/                 one folder per skill (SKILL.md + optional references/scripts/templates)
third-party-sources.json  upstream index with pinned versions
scripts/
  build-readme.py       regenerate the tables above
  validate-skills.py    CI check: valid frontmatter, names, bodies
  update-third-party.sh re-pull third-party sources
  sync-from-private.sh  mirror + scrub + leak-gate from the private workspace
  scrub_gate.py         scrub / leak-gate used by the sync
.github/workflows/      validate skills on PR; weekly third-party drift report
```

## License

MIT — see [LICENSE](LICENSE).
