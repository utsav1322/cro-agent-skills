#!/usr/bin/env python3
"""Scrub + leak-gate for the public skill library.

  scrub_gate.py scrub <dir>   neutralize brand tokens / internal paths / memory links, then gate
  scrub_gate.py gate  <dir>   scan only; exit 1 if anything private is found

Generic checks (always on): the org brand token, email addresses, absolute user /
workspace paths, and memory `[[links]]`.

Client / people / private-infra proper nouns are NOT hardcoded here (that list would
itself be sensitive). Supply them out-of-band via a blocklist file — one lowercase
token per line, `#` comments allowed — pointed to by the AGENT_SKILLS_BLOCKLIST env var.
The private sync step passes its own blocklist; the public CI gate runs without one.
"""
import os
import re
import sys

EXTS = (".md", ".py", ".sh", ".txt", ".json", ".js", ".ts", ".yml", ".yaml", ".html", ".css")

# Flag the brand token in prose, but allow the org's own GitHub paths — "unfoldcro/<repo>"
# and "unfoldcro-skills" — which legitimately appear in this repo's own URLs.
BRAND_RE = re.compile(r"\b(unfoldcro|ufc)\b(?![/-])", re.I)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PATH_RE = re.compile(r"/Users/\w+[^\s`\"']*")
MEMLINK_RE = re.compile(r"\[\[[a-z0-9-]+\]\]")
# Workspace-folder name to neutralize during scrub; overridable, not hardcoded to anything private.
WORKSPACE = os.environ.get("AGENT_SKILLS_WORKSPACE", "")


def load_extra_blocklist():
    path = os.environ.get("AGENT_SKILLS_BLOCKLIST", "")
    if not path or not os.path.isfile(path):
        return None
    toks = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip().lower()
        if line:
            toks.append(re.escape(line))
    if not toks:
        return None
    return re.compile(r"\b(" + "|".join(toks) + r")\b", re.I)


def brand_sub(text):
    text = re.sub(r"\bUnfoldCRO\b", "the agency", text)
    text = re.sub(r"\bunfoldcro\b", "the-org", text)
    text = re.sub(r"\bUFC\b", "the agency", text)
    text = re.sub(r"\bufc\b", "org", text)
    if WORKSPACE:
        text = re.sub(re.escape(WORKSPACE), "<workspace>", text)
    text = re.sub(r"/Users/[^/\s`\"']+", "~", text)
    text = re.sub(r"\[\[([a-z0-9-]+)\]\]", r"`\1`", text)
    return text


SELF = os.path.basename(__file__)


def walk(d):
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(EXTS) and f != SELF:  # the scanner's own source holds the patterns it detects
                yield os.path.join(root, f)


def scrub(d):
    n = 0
    for p in walk(d):
        try:
            t = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        nt = brand_sub(t)
        if nt != t:
            open(p, "w", encoding="utf-8").write(nt)
            n += 1
    print(f"scrubbed {n} files")


def gate(d):
    extra = load_extra_blocklist()
    checks = [("brand", BRAND_RE), ("email", EMAIL_RE), ("path", PATH_RE), ("memory-link", MEMLINK_RE)]
    if extra is not None:
        checks.append(("blocklist", extra))
    hits = []
    for p in walk(d):
        try:
            t = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        rel = os.path.relpath(p, d)
        for ln, line in enumerate(t.splitlines(), 1):
            for label, rx in checks:
                m = rx.search(line)
                if m:
                    hits.append(f"{rel}:{ln}: {label}: {m.group(0)}")
    if hits:
        print("LEAK GATE FAILED:", file=sys.stderr)
        print("\n".join(hits), file=sys.stderr)
        print(f"FAIL: {len(hits)} private references", file=sys.stderr)
        return 1
    print("LEAK GATE PASSED: no private references found")
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("scrub", "gate"):
        print(__doc__)
        return 2
    mode, d = sys.argv[1], sys.argv[2]
    if mode == "scrub":
        scrub(d)
    return gate(d)


if __name__ == "__main__":
    raise SystemExit(main())
