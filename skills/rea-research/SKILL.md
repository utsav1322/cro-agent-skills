---
name: rea-research
description: 'Evaluate REA for authorized reverse engineering of binaries, Electron apps, closed-source JavaScript, Android packages or observed runtime behavior. Use for reverse-engineering research when source is unavailable. Do not install automatically.'
---

# REA research (on demand)

Official upstream: https://github.com/morluto/rea
Official project: https://rea.tools/
Package: `rea-agents` (verify the actual release and checksum before installation).

## Routing gate

Use this reference **only when ordinary source inspection and existing debugging tools cannot answer the question**, and the target belongs to the agency or the client has authorized the particular analysis.

Appropriate cases:
- Inspect a supplied Electron application or JavaScript bundle with no usable source.
- Investigate documented runtime behavior in a user-owned, isolated browser.
- Inspect Android packages or native binaries when the project genuinely requires it and analysis is authorized.
- Compare permitted behavior across versions to understand interoperability or regressions.

Do not invoke for ordinary Shopify Liquid or theme tasks, public-site SEO/CRO audits, open-source repository understanding, screenshots alone, or routine Chrome DevTools diagnostics. Prefer the existing `seo-tech-stack`, `ecom-cro`, `shopify-ui-audit`, source inspection and browser tools.

## Safety and approval

1. **Research first.** Read the upstream README, SECURITY.md, DISCLAIMER.md, and relevant workflow instructions. Use the official repository as the source of installation instructions, not an arbitrary copied skill.
2. **Not an installation instruction.** Do not run `npx`, `npm install`, `rea setup`, `rea update`, scripts, or MCP registration merely because this skill was loaded. Get explicit user approval for installation or configuration changes.
3. **Least privilege.** Use an isolated development environment and disposable browser profile without client logins or unrelated secrets. Never use production credentials or private third-party binaries unless separately authorized.
4. **Authorization per target.** Being able to access a site or binary is not permission to bypass authentication, DRM, licensing, anti-bot controls or to copy protected code/assets.
5. **Separate permission for active actions.** A read-only artifact review does not authorize program execution, browser actions, attaching to a process, device changes, interception, network probing, or production changes. Explain impact and obtain approval.
6. **Pin releases.** When approved, use an inspected and pinned release; avoid unattended `@latest` installation and auto-updates. Review dependencies and setup dry-run before changes.
7. **Evidence and uncertainty.** Report observed artifacts, versions, timestamps, limitations and uncertainty. Do not present reverse-engineered inferences as source-verified facts.
8. **Do not import code.** Implement independently using functional requirements and original assets, subject to client ownership and applicable licenses.

## Decision output

Return one of:
- **Not needed:** existing source/browser tooling can complete the task.
- **Useful, no installation:** provide investigation plan and requested evidence.
- **Install proposed, approval required:** show exact package version, installation scope, configuration changes, credentials/process/browser exposure, rollback plan and prerequisites.

No automatic installations, runtime observation, client access, or production actions.
