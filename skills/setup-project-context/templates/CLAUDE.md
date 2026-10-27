# <Project>

<One line: what it is.> Type: <App|WordPress|Shopify theme|Content> · Client: <name|the agency> · Repo: <private|client-shared|public|none>

## Hard rules

<!-- Project-specific only; violation = data loss, leak, outage, client breach or money. ≤12 bullets. Never repeat global rules. No deploy line (global gate covers it). Soft rules go to docs/06-AGENTS.md. -->
- <rule>

## Stack

- <framework + version> · <DB> · <auth> · <host / process>

## Commands

- Dev `<cmd>` · Build `<cmd>` · Test `<cmd>` · Lint `<cmd>`

## Docs map

Open only what the task needs. `+local`: also read the slot's `.local.md`. `unwritten`: create it from the code when first needed. Verbatim sources: `docs/ref/`.

| Need | Read |
|---|---|
| Goals, approved scope, client asks | docs/01-PRD.md |
| UI, tokens, components | docs/02-DESIGN.md |
| Structure, modules, decisions | docs/03-ARCHITECTURE.md |
| Schema, migrations, seeds | docs/04-DATABASE.md |
| Routes, endpoints, webhooks | docs/05-API.md |
| Autonomy, workflows, project skills | docs/06-AGENTS.md |
| Client, URLs, environments, access pointers | docs/07-README.md |
| Phase, task queue, blockers | docs/08-IMPLEMENTATION.md |
| Local setup, env var names | docs/09-SETUP.md |
| Feature specs, how features are built | docs/10-FEATURES.md |
| Auth, roles, security | docs/11-AUTH-SECURITY.md |
| MCP / AI tooling for this project | docs/12-MCP.md |
| Third-party services, tracking IDs | docs/13-INTEGRATIONS.md |
| Tests, QA checklists | docs/14-TESTING-QA.md |
| Gotchas, known issues | docs/15-DEBUGGING.md |
| Deploy, release, rollback | docs/16-DEPLOYMENT.md |
| What shipped when | docs/17-CHANGELOG.md |

<!-- Keep only rows for slots that apply to the type (see the standard §4). Mark missing files `unwritten`, files with a .local.md `+local`. -->
N/A: <slots that cannot apply, or delete this line>
