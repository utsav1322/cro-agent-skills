# Good Repos — a tracked library

A curated list of Claude Code skill, plugin, and tooling repos worth knowing about, with our verdict on each. Reviewed monthly (see the log at the bottom); entries move between sections as upstreams change.

Verdicts: **Adopted** (in use) · **Subset** (we took part of it) · **Watching** (promising, not yet in use) · **Parked** (deferred, has a blocker) · **Skipped** (evaluated, not worth it for us).

## Skills & skill packs

| Repo | What it offers | Verdict | Notes |
|---|---|---|---|
| [garrytan/gstack](https://github.com/garrytan/gstack) | QA/browser, ship, review, debug, planning workflow toolkit | Adopted | Self-updating via its own upgrade skill |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | CRO, ads, analytics, attribution, social, copy, popups | Adopted | 12 skills |
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | ~25 technical/content/local SEO skills + site audit | Adopted | Full pack |
| [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | Official WordPress dev skills (plugins, REST, WP-CLI, perf) | Adopted | 6 skills |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | Web motion + Apple-style fluid UI design engineering | Adopted | 9 skills (native/Swift/Sonner-only ones skipped) |
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | GEO / AI-search (citability, crawlers, llms.txt, platforms) | Subset | 5-skill subset, pinned commit; ships an unused webapp/white-label dir |
| [Shopify/liquid-skills](https://github.com/Shopify/liquid-skills) | Official Shopify Liquid theme skills | Subset | a11y skill only |
| [mattpocock/skills](https://github.com/mattpocock/skills) | TypeScript / testing skills | Subset | TDD skill only |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Security tooling skills | Subset | supply-chain dependency auditor only; needs `uv` |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | Fresh Reddit/X/YouTube/HN research over last 30 days | Adopted | Keep its `assets/` dir |
| [obra / superpowers (official marketplace)](https://github.com/obra/superpowers) | Methodology plugin: plans, parallel agents, review, TDD, debugging | Skipped | 15 skills, all overlap our dev / review / plan / tdd / investigate skills; pure context cost |
| [zubair-trabzada/ai-marketing-claude](https://github.com/zubair-trabzada/ai-marketing-claude) | Marketing skill pack | Skipped | Overlaps marketingskills; no unique capability |
| [kepano/kepano-obsidian](https://github.com/kepano/kepano-obsidian) | Obsidian setup/config | Skipped | Not Claude skills; personal note-taking |

## Plugins

| Repo / marketplace | What it offers | Verdict | Notes |
|---|---|---|---|
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Always-on terse output mode | Adopted | v4.0.1, active |
| cloudflare (official plugin) | Cloudflare Workers/DNS/security skills + MCP | Adopted | |
| higgsfield (official plugin) | Media generation (image/video/audio) MCP + skills | Adopted | |
| shopify-ai-toolkit (official plugin) | Shopify dev surface skill | Adopted | |
| liquid-lsp (official plugin) | Liquid language server | Adopted | |

## Tools & agents (non-skill)

| Repo | What it offers | Verdict | Notes |
|---|---|---|---|
| [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | Multi-platform outreach / social automation | Parked | Core only; needs social-account cookies we won't wire |
| [vxcontrol/pentagi](https://github.com/vxcontrol/pentagi) | Autonomous pentest agent | Skipped | Heavy infra; out of scope for day-to-day work |
| [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | Local audio→text (Whisper) + TTS desktop app | Skipped | Trialed and removed; standalone app, not a skill |
| [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) | Debloat any Android/Google TV over Wi-Fi via ADB; Apple-TV-style launcher | Noted | Standalone app (Java, ~33k★), not a Claude skill; useful utility |

## Terse-output comparison (why caveman)

Several repos offer a compressed / low-token output style. We compared them and chose **caveman**:

| Option | Approach | Verdict |
|---|---|---|
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Terse "caveman" voice; keeps all technical payload; persistent toggle; packaged plugin | Adopted |
| Karpathy-style terse prompts | Prompt-only, no packaging, no mode persistence | Skipped — no toggle/persistence |
| Other "ultrafast/minimal" prompt gists | Drop detail to save tokens | Skipped — lose technical substance |

caveman won on: keeps every fact/command/path exact, has an on/off toggle that persists across a session, and ships as a maintained plugin with a marketplace update path.

## CRO Agent Skills vs other skill libraries

How this repo compares to other public Claude Code skill collections. Most are either single-domain packs or raw dumps; this one is a curated, opinionated, security-gated set across several domains, with verdicts and a monthly-maintained repo index.

| Repo | Scope | Curated / opinionated | Security-scrubbed | Maintained cadence | Comparison / verdicts |
|---|---|---|---|---|---|
| **CRO Agent Skills** (this repo) | Multi-domain: dev, planning, SEO, security, data, legal | Yes — verdicts + skip reasons | Yes — leak gate on every publish | Monthly review + third-party drift | Yes — this file |
| anthropics/skills (official) | General/reference examples | Reference, not opinionated | n/a | Per release | No |
| obra/superpowers | Dev methodology | Yes | n/a | Active | No |
| coreyhaines31/marketingskills | Marketing only | Yes | n/a | Active | No |
| AgriciDaniel/claude-seo | SEO only | Yes | n/a | Active | No |
| emilkowalski/skills | Motion/UI only | Yes | n/a | Active | No |
| awesome-claude-* lists | Link lists | Links, no verdicts | n/a | Varies | Link-only, no verdicts |

What makes this one worth a star:
- **One opinionated set, many domains** — not a single-topic pack, not a raw link dump.
- **Honest verdicts** — every tracked repo is marked Adopted / Subset / Parked / Skipped with a reason (this file).
- **Safe to copy** — a leak gate runs before anything is published; no secrets, no client data.
- **Kept fresh** — monthly review + automated drift checks on the upstreams it depends on.

## How this list is maintained

- Reviewed on the **1st of each month** (a scheduled workflow opens a reminder issue).
- Each review: re-check adopted upstreams for drift (`scripts/update-third-party.sh --check`), reconsider Parked/Watching entries, add newly-found repos, and record the pass in the log below.
- Adopted entries also appear in [`third-party-sources.json`](third-party-sources.json) with pinned versions.

## Review log

### Reviewed 2026-10
- Initial library. Adopted set matches `third-party-sources.json`. Skipped: superpowers (full overlap), ai-marketing-claude (overlap), pentagi (scope), kepano-obsidian (not skills), VoiceStudio (standalone app). Parked: Agent-Reach (needs social cookies).
