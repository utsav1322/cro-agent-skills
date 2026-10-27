#!/usr/bin/env python3
"""Static validation of locally maintained Claude skill metadata."""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
KEY = re.compile(r"^([a-z][a-z0-9-]*):\s*(.*)$")
NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def inspect(path: pathlib.Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path.relative_to(ROOT)}: missing YAML frontmatter"]
    close = text.find("\n---\n", 4)
    if close < 0:
        return [f"{path.relative_to(ROOT)}: unclosed YAML frontmatter"]
    fields: dict[str, str] = {}
    for line in text[4:close].splitlines():
        match = KEY.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("'\"")
    name = fields.get("name", "")
    description = fields.get("description", "")
    if name != path.parent.name or not NAME.fullmatch(name):
        problems.append(f"{path.relative_to(ROOT)}: name must match skill directory")
    if not description:
        problems.append(f"{path.relative_to(ROOT)}: missing description")
    if not text[close + 5:].strip():
        problems.append(f"{path.relative_to(ROOT)}: empty skill body")
    return problems


def main() -> int:
    files = sorted(SKILLS.glob("*/SKILL.md"))
    problems = []
    for path in files:
        problems.extend(inspect(path))
    for folder in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        if not (folder / "SKILL.md").is_file():
            problems.append(f"{folder.relative_to(ROOT)}: SKILL.md missing")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print(f"FAIL: {len(problems)} findings in {len(files)} skills", file=sys.stderr)
        return 1
    print(f"PASS: {len(files)} skills have valid names, descriptions, and bodies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
