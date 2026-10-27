#!/usr/bin/env python3
"""Rebuild the skill tables in README.md.

Own skills come from skills/*/SKILL.md. Third-party sources come from
third-party-sources.json (listed, not vendored). Only the text between the
<!-- OWN-SKILLS:START/END --> and <!-- THIRD-PARTY:START/END --> markers is replaced.

Usage: python3 scripts/build-readme.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "third-party-sources.json"

CATEGORIES = [
    ("Project & workflow", ["project-start", "task-dispatch", "capability-intake", "context-audit",
                            "setup-project-context", "update-md", "build-review-loop", "llm-council"]),
    ("Development & architecture", ["dev-agents", "dev-patterns", "backend-architecture",
                                    "frontend-system-design", "technical-feasibility", "rea-research"]),
    ("Planning & delivery", ["idea-validator", "requirements-business-analyst", "project-estimation-planning",
                             "competitor-market-analysis", "tech-research-intelligence", "sop-process-builder"]),
    ("SEO & ecommerce", ["seo-tech-stack", "shopify-ui-audit", "make-slides"]),
    ("Security & data", ["secrets-credential-manager", "password-authentication-security",
                         "data-privacy-security", "data-analysis-insights", "site-incident"]),
    ("Legal & compliance (research support, not legal advice)",
     ["international-legal-research", "privacy-data-protection-law",
      "intellectual-property-licensing", "legal-document-drafter"]),
]


def frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fm = m.group(1) if m else ""
    name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
    name = name_m.group(1).strip().strip("'\"") if name_m else path.parent.name
    desc = ""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            val = line[len("description:"):].strip()
            if val in ("|", ">", "|-", ">-", ""):
                buf = []
                for nxt in lines[i + 1:]:
                    if nxt.startswith((" ", "\t")) or not nxt.strip():
                        buf.append(nxt.strip())
                    else:
                        break
                val = " ".join(b for b in buf if b)
            desc = val.strip().strip("'\"").replace('\\"', '"')
            break
    return name, re.sub(r"\s+", " ", desc)


def short(desc, limit=170):
    desc = desc.replace("|", "/")
    if len(desc) <= limit:
        return desc
    return desc[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def own_table():
    found = {p.parent.name: frontmatter(p)[1] for p in sorted(SKILLS.glob("*/SKILL.md"))}
    out, used = [], set()
    for title, names in CATEGORIES:
        rows = [n for n in names if n in found]
        if not rows:
            continue
        out.append(f"### {title}\n\n| Skill | What it does |\n|---|---|")
        for n in rows:
            out.append(f"| [`{n}`](skills/{n}/SKILL.md) | {short(found[n])} |")
            used.add(n)
        out.append("")
    rest = sorted(n for n in found if n not in used)
    if rest:
        out.append("### Other\n\n| Skill | What it does |\n|---|---|")
        out += [f"| [`{n}`](skills/{n}/SKILL.md) | {short(found[n])} |" for n in rest]
        out.append("")
    return "\n".join(out).rstrip() + "\n", len(found)


def third_party_table():
    d = json.loads(MANIFEST.read_text())
    out = ["| Source | Skills / plugins | Fetch |", "|---|---|---|"]
    for e in d.get("npx_skills", []):
        sk = ", ".join(f"`{s}`" for s in e["skills"])
        out.append(f"| [{e['repo']}](https://github.com/{e['repo']}) | {sk} | `{e.get('install','')}` |")
    for e in d.get("manual_pinned", []):
        sk = ", ".join(f"`{s}`" for s in e["skills"])
        out.append(f"| [{e['repo']}](https://github.com/{e['repo']}) (pinned) | {sk} | hand-copy at pinned commit |")
    for e in d.get("self_updating", []):
        repo = e.get("repo", "")
        link = f"[{repo}](https://github.com/{repo})" if repo else e["name"]
        out.append(f"| {link} | `{e['name']}` | self-updating (gstack-upgrade) |")
    plugins = d.get("plugins", [])
    if plugins:
        out.append("")
        out.append("**Plugins** (install from their marketplace, keep current with the update command):")
        out.append("")
        out.append("| Plugin | Update |")
        out.append("|---|---|")
        for p in plugins:
            out.append(f"| `{p['name']}` | `{p.get('update','')}` |")
    return "\n".join(out) + "\n"


def replace_block(text, marker, body):
    pat = re.compile(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"README.md missing {marker} markers")
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def main():
    readme = README.read_text(encoding="utf-8")
    table, total = own_table()
    readme = replace_block(readme, "OWN-SKILLS", table)
    readme = re.sub(r"(<!-- OWN-COUNT -->)\d+(<!-- /OWN-COUNT -->)", rf"\g<1>{total}\g<2>", readme)
    readme = replace_block(readme, "THIRD-PARTY", third_party_table())
    README.write_text(readme, encoding="utf-8")
    print(f"README.md updated: {total} skills")


if __name__ == "__main__":
    main()
