#!/usr/bin/env python3
"""docsmig — move project docs onto the docs/01–17 standard.

Spec: ~/.claude/references/project-docs-standard.md
Run with: python3 -I docsmig.py [--run DIR] <command> ...

Commands
  activity [--force]            last-touched snapshot of every project (run once, before any write)
  preflight [--fetch] [slug..]  inventory + mode per project -> inventory.json / inventory.tsv
  prepare <slug> [--force] [--mode git|in-place]   lock, snapshot legacy docs, write plan.json, create empty out/
  verify <slug>                 check out/ against the snapshot and the standard
  commit <slug>                 git mode, repos WITHOUT a remote only: commits onto branch docs-restructure
                                (no checkout, no index, no hooks)
  localize <slug> [--check] [--link-from DIR] [--ack-upstream-docs]
                                git mode, repos with a remote: docs stay on this machine — one commit untracks the
                                legacy docs; the index goes to .claude/CLAUDE.md, the rest on disk, all ignored via
                                .git/info/exclude; nothing pushed. --link-from: link to a shared folder (worktrees)
  materialize <slug> <dir>      write a verified out/ into a shared docs folder for --link-from
  apply <slug>                  in-place mode: copy out/ into the project, delete migrated legacy files
  adopt <slug>                  repos without a remote, after user approval only: fast-forward docs-restructure
  restore <slug> [--after-adopt|--after-localize]    roll back without losing later edits
  audit <slug|path> [--fix]     compliance check of a live project; refreshes a localized repo's mirror of its docs
                                (--fix restores missing local docs from that mirror and the AGENTS.md link)
  status                        one line per prepared project

Exit codes: 0 ok · 10 verify failed · 20 drift · 30 manual · 2 usage/internal error
"""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
WS = HOME / "Desktop" / "<workspace>"
CATEGORIES = ["Custom", "Shopify", "the agency", "WordPress", "SEO", "MCP"]
TOP_LEVEL_PROJECTS = ["example-project"]
EXCLUDED = {
    "Shopify/_archive": "archive",
    "MCP/external": "stub notes, not a project",
    "example-incident-YYYY-MM-DD": "incident record with credentials",
    "tools/Claude SEO Skills": "skills pack, not a project",
}
MANUAL_FIXED = {
    "the agency/claude-code-toolkit": "post-commit auto-publish hook; sanitize.sh must exclude new slots",
    "the agency/the-org-brand-guidelines": "files referenced by path from ~/.claude/rule.md",
}
BRANCH = "docs-restructure"
EXIT_OK, EXIT_FAIL, EXIT_DRIFT, EXIT_MANUAL, EXIT_USAGE = 0, 10, 20, 30, 2

SLOTS = {1: "PRD", 2: "DESIGN", 3: "ARCHITECTURE", 4: "DATABASE", 5: "API", 6: "AGENTS", 7: "README",
         8: "IMPLEMENTATION", 9: "SETUP", 10: "FEATURES", 11: "AUTH-SECURITY", 12: "MCP", 13: "INTEGRATIONS",
         14: "TESTING-QA", 15: "DEBUGGING", 16: "DEPLOYMENT", 17: "CHANGELOG"}
SLOT_FILES = {"%02d-%s.md" % (n, s): n for n, s in SLOTS.items()}
LOCAL_FILES = {"%02d-%s.local.md" % (n, s): n for n, s in SLOTS.items()}
ALL = set(SLOTS)
MATRIX = {
    "app": ALL,
    "wordpress": ALL,
    "shopify-theme": {1, 2, 3, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17},
    "content": {1, 6, 7, 8, 12, 13, 15, 17},
}
NEVER_BACKFILL = {1, 7, 8, 15, 17}

PRUNE_DIRS = {"node_modules", ".git", "vendor", ".next", "dist", "build", "uploads", ".turbo", ".cache",
              "__pycache__", ".venv", "venv", ".svelte-kit", ".output", "coverage", ".playwright-mcp"}
SENSITIVE_GLOBS = ["vault*", "*secret*", "*credential*", "*password*", ".env*", "*.pem", "*.key", "id_rsa*",
                   "id_ed25519*", "*.kdbx", "login-credentials*"]
ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template", ".env.dist"}
PINNED_ROOT = {"readme.md", "readme", "agents.md", "security.md", "code_of_conduct.md", "contributing.md",
               "license.md", "license", "version"}
CONDITIONAL_PINNED = {"changelog.md", "learnings.md"}  # pinned only when CI/scripts read them
LEGACY_DIRS_AT_ROOT = {"plans", "notes", "spec", "specs"}
TOOL_OWNED_PREFIXES = ("audits/", "docs/superpowers/", ".github/")
PINNED_PREFIXES = ("docs/ref/", ".claude/skills/")  # existing files there are never moved or overwritten
TEXT_SUFFIXES_SKIP = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf", ".zip", ".gz", ".woff",
                      ".woff2", ".ttf", ".eot", ".mp4", ".mov", ".mp3", ".lock", ".map", ".min.js"}

SECRET_RES = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{22,}"),
    re.compile(r"shp(?:at|ss|ca|pa)_[a-fA-F0-9]{32}"),
    re.compile(r"(?:sk|rk|pk)_(?:live|test)_[0-9a-zA-Z]{16,}"),
    re.compile(r"whsec_[A-Za-z0-9]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])sk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}"),
    re.compile(r"xox[abeprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"rzp_(?:live|test)_[A-Za-z0-9]{10,}"),
    re.compile(r"\bnpg_[A-Za-z0-9]{10,}"),
    re.compile(r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
]
SECRET_KEYS = (r"(?:password|passwd|pass|pwd|pw|secret|token|salt|api[ _-]?key|access[ _-]?key|private[ _-]?key|secret[ _-]?key"
               r"|app[ _-]?key|license[ _-]?key|client[ _-]?secret|auth[ _-]?key|encryption[ _-]?key|[A-Za-z0-9]+_key)")
STRONG_KEY_RE = re.compile(r"(?i)(password|passwd|pass|pwd|\bpw\b|secret|token|salt|api[ _-]?key|access[ _-]?key|private[ _-]?key"
                           r"|secret[ _-]?key|app[ _-]?key|license[ _-]?key|client[ _-]?secret|auth[ _-]?key|encryption[ _-]?key)")
EMAIL_PASS_RE = re.compile(r"`?[\w.+-]+@[\w-]+(?:\.[\w-]+)+`?\s*/\s*`([^`\s/]{6,})`")
BACKTICK_KEY_RE = re.compile(r"(?i)\b(?:api\s*)?(?:key|token|secret|password|passwd|pwd)\b\s*[:=]\s*`([^`\s]{16,})`")
CLI_SECRET_RES = [
    re.compile(r"(?i)\bmysql(?:dump)?\b[^\n]*\s-p['\"]?([^\s'\"]{4,})"),
    re.compile(r"(?i)\bsshpass\s+-p\s*['\"]?([^\s'\"]{4,})"),
    re.compile(r"(?i)\bcurl\b[^\n]*\s(?:-u|--user)\s+['\"]?[^\s:'\"]+:([^\s'\"]{4,})"),
    re.compile(r"(?i)authorization:\s*(?:bearer|basic|token)\s+([A-Za-z0-9._~+/=-]{16,})"),
]
HEX_COLOR_RE = re.compile(r"^#?[0-9A-Fa-f]{3,8}$")
NON_SECRET_LABELS = {"user", "username", "login", "host", "hostname", "port", "server", "ip", "email", "path", "url",
                     "domain", "id", "account", "alias", "dir", "directory", "home", "region", "database", "db", "name"}
TABLE_CRED_RE = re.compile(r"\|\s*([\w.@+-]{3,})\s*\|\s*([^\s|]{8,})\s*\|")
ASSIGN_RE = re.compile(r"(?i)\b([A-Za-z0-9_.-]*%s[A-Za-z0-9_.-]*)\s*[:=]\s*[\"']?([^\s\"'`<>]{8,})" % SECRET_KEYS)
QUOTED_RE = re.compile(r"""(?i)["']([A-Za-z0-9_.-]*%s[A-Za-z0-9_.-]*)["']\s*(?:=>|:|,)\s*["']([^"']{8,})["']""" % SECRET_KEYS)
URL_CRED_RE = re.compile(r"[a-z][a-z0-9+.-]*://([^\s:/@]+):([^\s@/]{3,})@", re.I)
PLACEHOLDER_RE = re.compile(r"(?i)^(fill[_-]?me|change[_-]?me|your[_-].*|x{3,}|\*{3,}|placeholder|example.*|redacted"
                            r"|dummy|password|secret|\$\{?[A-Za-z_]+\}?|<[^>]*>|\.{3,}|required|optional|vault.*)$")
CRED_CONTEXT_RE = re.compile(r"(?i)\b(admin|login|user(name)?|ftp|sftp|ssh|wp|db|cpanel|credentials?|pass(word)?)\b")
CRED_LEAD_RE = re.compile(r"(?i)\b(admin|login|user(name)?|ftp|sftp|ssh|wp|db|cpanel|credentials?|pass(word)?)\b\s*[:=-]?\s*$")
USER_PASS_RE = re.compile(r"([\w.@+-]{3,})\s+/\s+([^\s/]{8,})")
BLOCK_COMMENT_RE = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}|<!--.*?-->|/\*.*?\*/", re.S)
COMMENT_PREFIXES = ("//", "#", "*", "/*", "<!--", "--", ";", "'" * 3, '"' * 3)
AI_WORDS = re.compile(r"(?i)\b(claude|codex|chatgpt|openai|anthropic|co-authored-by|generated with)\b")
POINTER_STOP = {"see", "read", "check", "refer", "to", "in", "the", "for", "more", "details", "detail", "full", "and",
                "before", "after", "update", "updated", "file", "files", "doc", "docs", "notes", "note", "also", "here",
                "there", "at", "of", "on", "a", "an", "is", "are", "moved", "from", "into", "this", "that", "info",
                "lives", "live", "kept", "now", "only", "it", "its"}


class DocsmigError(Exception):
    def __init__(self, msg, code=EXIT_USAGE):
        super().__init__(msg)
        self.code = code


# ----------------------------------------------------------------- helpers

def today():
    return datetime.date.today().isoformat()


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def default_run():
    env = os.environ.get("DOCSMIG_RUN")
    if env:
        return Path(env).expanduser()
    return WS / "_backups" / ("docs-migration-" + today())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return []


def norm(line):
    s = line.strip()
    s = re.sub(r"^#{1,6}\s*", "", s)
    s = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)  # a plain line may become a bullet and vice versa
    s = re.sub(r"\s+", " ", s)
    return s


def significant(s):
    return len(re.sub(r"[^A-Za-z0-9]", "", s)) >= 8


MD_TOKEN_RE = re.compile(r"[\w./-]*\.md\b")
MD_REF_RE = re.compile(r"\[[^\]]*\]\([^)\s]*\.md(?:#[^)]*)?\)|`[^`]*\.md(?:#[^`]*)?`|(?<![\w-])[\w./-]+\.md\b", re.I)


def is_pointer(line):
    """True only when the line references a .md file and carries (almost) nothing else — no facts of its own."""
    s = norm(line)
    if not MD_REF_RE.search(s):
        return False
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r" \1 ", s)  # keep link text — it is content; drop only the target
    s = MD_REF_RE.sub(" ", s)
    words = [w for w in re.findall(r"[A-Za-z0-9]+", s) if w.lower() not in POINTER_STOP]
    return len("".join(words)) <= 8


def char_classes(v):
    return sum(bool(re.search(c, v)) for c in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))


def has_secret(line):
    if any(r.search(line) for r in SECRET_RES):
        return True
    for rx in (ASSIGN_RE, QUOTED_RE):
        for m in rx.finditer(line):
            key, val = m.group(1), m.group(2).strip(",;.)")
            if PLACEHOLDER_RE.match(val):
                continue
            if STRONG_KEY_RE.search(key):
                if re.search(r"\d", val) or len(val) >= (12 if rx is QUOTED_RE else 16):
                    return True
            elif char_classes(val) >= 3 or (re.search(r"\d", val) and re.search(r"[A-Za-z]", val) and len(val) >= 20):
                return True  # generic *_key: only values that look random
    for m in BACKTICK_KEY_RE.finditer(line):  # e.g. "Key = `abcd…`", "token: `…`"
        v = m.group(1)
        if not PLACEHOLDER_RE.match(v) and re.search(r"\d", v) and re.search(r"[A-Za-z]", v) and "/" not in v:
            return True
    for m in EMAIL_PASS_RE.finditer(line):  # "`user@host` / `password`" credential pair
        v = m.group(1)
        if "@" not in v and not PLACEHOLDER_RE.match(v) and char_classes(v) >= 2:
            return True
    for rx in CLI_SECRET_RES:
        for m in rx.finditer(line):
            if not PLACEHOLDER_RE.match(m.group(1)):
                return True
    if CRED_CONTEXT_RE.search(line):
        for m in TABLE_CRED_RE.finditer(line):
            label, val = m.group(1).lower(), m.group(2).strip("`'\"")
            if HEX_COLOR_RE.match(val) or "/" in val:
                continue  # colours and file paths, not passwords
            if label in NON_SECRET_LABELS:
                continue  # usernames, hosts, ports are pointers, not secrets
            if char_classes(val) >= 3 and not PLACEHOLDER_RE.match(val):
                return True
    for m in URL_CRED_RE.finditer(line):
        if not PLACEHOLDER_RE.match(m.group(2)):
            return True
    if CRED_CONTEXT_RE.search(line):
        for m in USER_PASS_RE.finditer(line):
            if not CRED_LEAD_RE.search(line[:m.start()]) and not CRED_CONTEXT_RE.fullmatch(m.group(1)):
                continue  # a credential label must sit right before the "user / pass" pair
            pw = m.group(2).rstrip(".,;)")
            if HEX_COLOR_RE.match(pw) or HEX_COLOR_RE.match(m.group(1)):
                continue  # colour pairs like #00C853 / #0B6E4F
            if char_classes(pw) >= 3 and not PLACEHOLDER_RE.match(pw):
                return True
    return False


def is_sensitive(name):
    low = name.lower()
    if low in ENV_TEMPLATES:
        return False  # variable names only — backfill source for 09-SETUP
    return any(fnmatch.fnmatch(low, g) for g in SENSITIVE_GLOBS)


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k in ("GIT_SSH", "GIT_SSH_COMMAND")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra:
        env.update(extra)
    return env


def git(path, *args, env_extra=None, check=True, timeout=120):
    """Every git call: hooks disabled, no optional locks (never rewrites the real index), clean GIT_* env."""
    cmd = ["git", "-C", str(path), "-c", "core.hooksPath=/dev/null", "--no-optional-locks"] + list(args)
    r = subprocess.run(cmd, env=clean_env(env_extra), capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise DocsmigError("git %s failed: %s" % (" ".join(args[:3]), r.stderr.strip()))
    return r


def gout(path, *args, env_extra=None):
    r = git(path, *args, env_extra=env_extra, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def gz(path, *args):
    """NUL-separated output (safe for unicode/space paths)."""
    r = git(path, *args, check=False)
    return [x for x in r.stdout.split("\0") if x] if r.returncode == 0 else []


def slug_dir(slug):
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", slug.replace("/", "__"))
    return "%s-%s" % (clean, hashlib.sha1(slug.encode()).hexdigest()[:6])


def resolve(arg):
    p = Path(arg).expanduser()
    if not p.is_absolute():
        p = WS / arg
    p = p.resolve()
    if not p.is_dir():
        raise DocsmigError("not a project directory: %s" % arg)
    try:
        slug = str(p.relative_to(WS.resolve()))
    except ValueError:
        slug = p.name
    return slug, p


def all_projects():
    out = []
    for cat in CATEGORIES:
        base = WS / cat
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                out.append(("%s/%s" % (cat, d.name), d))
    for name in TOP_LEVEL_PROJECTS:
        d = WS / name
        if d.is_dir():
            out.append((name, d))
    tools = WS / "tools"
    if tools.is_dir():
        for d in sorted(tools.iterdir()):
            if d.is_dir():
                out.append(("tools/%s" % d.name, d))
    return out


def walk_files(root, max_depth=None):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = 0 if str(rel) == "." else len(rel.parts)
        keep = []
        for d in dirnames:
            if d in PRUNE_DIRS or d.startswith("_backup") or d == "_snapshots":
                continue
            if (Path(dirpath) / d / ".git").exists():
                continue  # nested repo: never descend
            keep.append(d)
        dirnames[:] = keep if (max_depth is None or depth < max_depth) else []
        for f in filenames:
            yield Path(dirpath) / f


def path_has_symlink(root, rel):
    parts = Path(rel).parts
    return any((Path(root) / Path(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1))


def safe_copy(src, dst, root=None):
    """Copy without ever writing through a symlink (file or any parent directory under root)."""
    dst = Path(dst)
    if dst.is_symlink() or (root is not None and path_has_symlink(root, dst.relative_to(root))):
        raise DocsmigError("refusing to write through symlink %s" % dst, EXIT_MANUAL)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def stash_to(run_sub, rel, src):
    """Move a file aside (rejected/ or pre-adopt/) instead of overwriting or deleting it."""
    dst = Path(run_sub) / rel
    if dst.exists():
        dst = dst.with_name(dst.name + "." + datetime.datetime.now().strftime("%H%M%S%f"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


# ----------------------------------------------------------------- detection

def detect_type(p):
    def has_theme(base):
        return (base / "layout" / "theme.liquid").is_file() and (base / "sections").is_dir()
    if has_theme(p) or any(has_theme(c) for c in p.iterdir() if c.is_dir() and not c.name.startswith(".")):
        return "shopify-theme", "layout/theme.liquid + sections/"
    if (p / "wp-content").is_dir() or (p / "wp-config.php").exists():
        return "wordpress", "wp-content / wp-config"
    for f in walk_files(p, max_depth=2):
        if f.name == "style.css" or f.suffix == ".php":
            try:
                head = f.read_text(encoding="utf-8", errors="ignore")[:2000]
            except OSError:
                continue
            if re.search(r"^\s*\*?\s*(Theme Name|Plugin Name):", head, re.M):
                return "wordpress", "%s header" % f.relative_to(p)
    for marker in ("package.json", "shopify.app.toml", "composer.json", "pyproject.toml", "requirements.txt",
                   "go.mod", "Cargo.toml"):
        if (p / marker).is_file():
            return "app", marker
    for f in walk_files(p, max_depth=2):
        if f.name == "manifest.json":
            try:
                if '"manifest_version"' in f.read_text(encoding="utf-8", errors="ignore")[:4000]:
                    return "app", "browser extension %s" % f.relative_to(p)
            except OSError:
                pass
    for f in walk_files(p, max_depth=2):
        if f.name in ("package.json", "shopify.app.toml", "composer.json", "pyproject.toml"):
            return "app", str(f.relative_to(p))
    return "content", "no code markers"


def nested_repos(p):
    found = []
    for dirpath, dirnames, filenames in os.walk(p):
        rel = Path(dirpath).relative_to(p)
        depth = 0 if str(rel) == "." else len(rel.parts)
        if depth > 0 and (".git" in dirnames or ".git" in filenames):
            found.append(str(rel))
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS] if depth < 3 else []
    return found


def git_facts(p):
    top = gout(p, "rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != p.resolve():
        return None
    gd = Path(gout(p, "rev-parse", "--absolute-git-dir"))
    common = Path(gout(p, "rev-parse", "--path-format=absolute", "--git-common-dir") or str(gd))
    wt = [l for l in gout(p, "worktree", "list", "--porcelain").splitlines() if l.startswith("worktree ")]
    remote = gout(p, "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", remote)
    owner = m.group(1) if m else ("local" if not remote else "other")
    default = ""
    sym = gout(p, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    for cand in ([sym] if sym else []) + ["origin/main", "origin/master", "main", "master"]:
        if cand and git(p, "rev-parse", "--verify", "--quiet", cand + "^{commit}", check=False).returncode == 0:
            default = cand
            break
    head = gout(p, "rev-parse", "--verify", "--quiet", "HEAD")
    branch = gout(p, "branch", "--show-current")
    ahead = behind = 0
    if default and head:
        lr = gout(p, "rev-list", "--left-right", "--count", "%s...HEAD" % default).split()
        if len(lr) == 2:
            behind, ahead = int(lr[0]), int(lr[1])
    hooks_path = gout(p, "config", "core.hooksPath")
    hooks = []
    hdir = (p / hooks_path) if hooks_path else (common / "hooks")
    if hdir.is_dir():
        hooks = sorted(h.name for h in hdir.iterdir() if h.is_file() and not h.name.endswith(".sample"))
    in_progress = [n for n in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
                   if (gd / n).exists()]
    fetch_head = common / "FETCH_HEAD"
    return {
        "git_dir": str(gd), "common_dir": str(common), "worktrees": len(wt), "linked_worktree": gd != common,
        "remote": remote, "owner": owner, "default_ref": default, "default_name": default.split("/")[-1],
        "head": head, "branch": branch, "ahead": ahead, "behind": behind, "hooks": hooks,
        "hooks_path": hooks_path, "in_progress": in_progress,
        "ignore_case": gout(p, "config", "--bool", "core.ignoreCase") == "true",
        "object_format": gout(p, "rev-parse", "--show-object-format") or "sha1",
        "last_fetch": datetime.datetime.fromtimestamp(fetch_head.stat().st_mtime).date().isoformat()
        if fetch_head.exists() else "",
        "branch_exists": git(p, "show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH, check=False).returncode == 0,
    }


def referenced_by_tooling(p, name):
    """Path of a CI/script/package.json file that mentions the doc (then the doc is pinned)."""
    pat = re.compile(re.escape(name), re.I)
    for f in walk_files(p, max_depth=3):
        rel = str(f.relative_to(p))
        if rel.startswith(".github/") or f.suffix in (".sh", ".yml", ".yaml") or f.name in ("package.json", "Makefile"):
            try:
                if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                    return rel
            except OSError:
                pass
    return ""


def classify_docs(p):
    """{relpath: class} for docs. Classes: legacy (migrated), pinned (stays), tool, sensitive."""
    res = {}
    for f in walk_files(p, max_depth=6):
        rel = f.relative_to(p)
        srel = str(rel)
        name = f.name
        low = name.lower()
        top = rel.parts[0]
        if is_sensitive(name):
            res[srel] = "sensitive"
            continue
        if srel.startswith(PINNED_PREFIXES):
            res[srel] = "pinned"
            continue
        if f.suffix.lower() != ".md" and low not in ("readme", "license", "version"):
            continue
        if srel.startswith(TOOL_OWNED_PREFIXES):
            res[srel] = "tool"
            continue
        if len(rel.parts) == 1:
            if low in PINNED_ROOT or low in ("claude.local.md", "agents.local.md"):  # v2 local index / Codex file
                res[srel] = "pinned"
            elif low in CONDITIONAL_PINNED and referenced_by_tooling(p, name):
                res[srel] = "pinned"
            else:
                res[srel] = "legacy"
            continue
        if top in ("docs",) or top in LEGACY_DIRS_AT_ROOT:
            res[srel] = "legacy"  # includes slot files that already exist (they are rewritten through out/)
    return res


def doc_states(p, rels, gf):
    """git state per path: tracked, dirty, untracked, ignored, case-mismatch (or 'local' outside git)."""
    if not gf:
        return {r: "local" for r in rels}
    if not rels:
        return {}
    tracked = set(gz(p, "ls-files", "-z", "--", *rels))
    lower_tracked = {}
    if gf["ignore_case"]:
        for t in gz(p, "ls-files", "-z"):
            lower_tracked[t.lower()] = t
    dirty = set()
    entries = gz(p, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames", "--", *rels)
    for e in entries:
        if len(e) > 3:
            dirty.add(e[3:])
    states = {}
    for r in rels:
        if r in tracked:
            states[r] = "dirty" if r in dirty else "tracked"
        elif gf["ignore_case"] and r.lower() in lower_tracked:
            states[r] = "case-mismatch"
        elif git(p, "check-ignore", "-q", "--no-index", "--", r, check=False).returncode == 0:
            states[r] = "ignored"
        else:
            states[r] = "untracked"
    return states


def activity_map(run_dir):
    res = {}
    for line in read_lines(run_dir / "activity.tsv")[1:]:
        cols = line.split("\t")
        if len(cols) >= 5:
            res[cols[0]] = {"last": cols[2], "last_commit": cols[3], "active": cols[4] == "yes"}
    return res


DOCS_MAP_RE = re.compile(r"^## Docs map\s*$", re.M | re.I)


def index_file(p):
    """The project index: .claude/CLAUDE.md in a repo whose docs were localized, CLAUDE.md everywhere else."""
    for name in (".claude/CLAUDE.md", "CLAUDE.local.md", "CLAUDE.md"):
        f = p / name
        try:
            if f.is_file() and DOCS_MAP_RE.search(f.read_text(encoding="utf-8", errors="replace")):
                return f
        except OSError:
            pass
    return p / "CLAUDE.md"


def has_docs_map(p):
    f = index_file(p)
    try:
        return f.is_file() and bool(DOCS_MAP_RE.search(f.read_text(encoding="utf-8", errors="replace")))
    except OSError:
        return False


def decide_mode(slug, p, gf, docs, states):
    """Returns (mode, reason, adopt_strategy)."""
    legacy = [r for r, c in docs.items() if c == "legacy"]
    if slug in EXCLUDED:
        return "skip", EXCLUDED[slug], ""
    if has_docs_map(p):
        return "skip", "already on the v2 standard (CLAUDE.md has a Docs map)", ""
    if slug in MANUAL_FIXED:
        return "manual", MANUAL_FIXED[slug], ""
    nested = nested_repos(p)
    if nested and not gf:
        return "manual", "container with nested repos: %s" % ", ".join(nested[:3]), ""
    links = sorted({r for r in legacy + ["CLAUDE.md", "docs", ".claude", ".claude/skills"] if (p / r).is_symlink()})
    if links:
        return "manual", "symlinked doc(s): %s" % ", ".join(links), ""
    if not gf:
        return "in-place", "not a git repo", ""
    if gf["worktrees"] > 1 or gf["linked_worktree"]:
        return "manual", "shared git dir with %d worktrees" % gf["worktrees"], ""
    if gf["in_progress"]:
        return "manual", "git operation in progress: %s" % ", ".join(gf["in_progress"]), ""
    if gf["branch_exists"]:
        return "manual", "branch %s already exists" % BRANCH, ""
    if not gf["head"]:
        return "manual", "repo has no commits", ""
    if not gf["branch"]:
        return "manual", "detached HEAD", ""
    lstates = [states[r] for r in legacy]
    if not legacy:
        ign = [git(p, "check-ignore", "-q", "--no-index", "--", x, check=False).returncode == 0
               for x in ("CLAUDE.md", "docs/01-PRD.md")]
        if all(ign):
            return "in-place", "no legacy docs; new docs would be gitignored (local-only)", ""
    elif "case-mismatch" in lstates:
        return "manual", "case-only rename pending: %s" % [r for r in legacy if states[r] == "case-mismatch"], ""
    if legacy and all(s == "ignored" for s in lstates):
        return "in-place", "all legacy docs gitignored (local-only)", ""
    if legacy and not any(s in ("tracked", "dirty") for s in lstates):
        return "manual", "legacy docs untracked but not ignored; repo tracks none", ""
    if gf["behind"] and gf["default_ref"]:
        base = gout(p, "merge-base", gf["default_ref"], "HEAD")
        changed = set(gz(p, "diff", "-z", "--no-renames", "--name-only", base, gf["default_ref"], "--")) if base else set()
        if changed & set(legacy) or any(c == "CLAUDE.md" or c.startswith("docs/") for c in changed):
            return "manual", "behind %s by %d with doc changes there (diverged)" % (gf["default_ref"], gf["behind"]), ""
    if not gf["remote"]:
        return "git", "local-only repo (no remote) — adopt by fast-forward", "ff"
    if gf["branch"] == gf["default_name"]:
        if gf["ahead"]:
            return "manual", "unpushed commits on %s (a PR would carry them)" % gf["branch"], ""
        return "git", "on %s — adopt via PR (push needs approval)" % gf["branch"], "pull"
    return "git", "feature branch %s — adopt by fast-forward" % gf["branch"], "ff"


# ----------------------------------------------------------------- commands: activity / preflight / prepare

def cmd_activity(args, run_dir):
    out = run_dir / "activity.tsv"
    if out.exists() and not args.force:
        print("activity.tsv exists (use --force to recompute): %s" % out)
        return EXIT_OK
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=60)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = ["project\tlast_file_mtime\tlast_file_date\tlast_commit\tactive"]
    for slug, p in all_projects():
        if slug in ("Shopify/_archive", "MCP/external"):
            continue
        last = 0
        for f in walk_files(p):
            try:
                last = max(last, int(f.lstat().st_mtime))
            except OSError:
                pass
        lc = gout(p, "log", "-1", "--format=%cs") if git_facts(p) else ""
        rows.append("%s\t%d\t%s\t%s\t%s" % (slug, last, datetime.date.fromtimestamp(last).isoformat() if last else
                                           "1970-01-01", lc, "yes" if last >= cutoff.timestamp() else "no"))
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    os.chmod(out, 0o600)
    print("wrote %s (%d projects)" % (out, len(rows) - 1))
    return EXIT_OK


def inventory_entry(slug, p, act, fetch=False):
    gf = git_facts(p)
    if gf and fetch and gf["remote"]:
        git(p, "fetch", "--no-tags", "--quiet", "origin", check=False, timeout=90)
        gf = git_facts(p)
    ptype, evidence = detect_type(p)
    docs = classify_docs(p)
    legacy = sorted(r for r, c in docs.items() if c == "legacy")
    states = doc_states(p, legacy, gf)
    mode, reason, strategy = decide_mode(slug, p, gf, docs, states)
    private = sorted(r for r in legacy if states.get(r) in ("ignored", "untracked")) if mode == "git" else []
    return {
        "slug": slug, "path": str(p), "type": ptype, "type_evidence": evidence,
        "active": act.get(slug, {}).get("active", False), "last_touched": act.get(slug, {}).get("last", ""),
        "mode": mode, "reason": reason, "adopt_strategy": strategy, "git": gf, "nested_repos": nested_repos(p),
        "legacy": legacy, "states": {r: states.get(r, "") for r in legacy}, "private": private,
        "pinned": sorted(r for r, c in docs.items() if c == "pinned"),
        "sensitive": sorted(r for r, c in docs.items() if c == "sensitive"),
    }


def cmd_preflight(args, run_dir):
    act = activity_map(run_dir)
    targets = [resolve(s) for s in args.slugs] if args.slugs else all_projects()
    inv = []
    for slug, p in targets:
        try:
            inv.append(inventory_entry(slug, p, act, fetch=args.fetch))
        except Exception as e:  # keep going; report per project
            inv.append({"slug": slug, "path": str(p), "mode": "manual", "reason": "preflight error: %s" % e})
    name = "inventory.json" if not args.slugs else "inventory-partial.json"
    (run_dir / name).write_text(json.dumps(inv, indent=1), encoding="utf-8")
    lines = ["slug\ttype\tactive\tmode\treason\tlegacy\tprivate\tdirty"]
    for e in inv:
        st = e.get("states", {})
        lines.append("\t".join([e["slug"], e.get("type", "?"), "yes" if e.get("active") else "no", e["mode"],
                                e["reason"], str(len(e.get("legacy", []))), str(len(e.get("private", []))),
                                str(sum(1 for v in st.values() if v in ("dirty", "untracked")))]))
    (run_dir / name.replace(".json", ".tsv")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    counts = {}
    for e in inv:
        counts[e["mode"]] = counts.get(e["mode"], 0) + 1
    print("modes: " + ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    if args.slugs:
        print("\n".join(lines))
    return EXIT_OK


def proj_run(run_dir, slug):
    return run_dir / slug_dir(slug)


def load_plan(run_dir, slug, p):
    f = proj_run(run_dir, slug) / "plan.json"
    if not f.exists():
        raise DocsmigError("no plan.json for %s — run prepare first" % slug)
    plan = json.loads(f.read_text(encoding="utf-8"))
    if Path(plan["path"]).resolve() != Path(p).resolve():
        raise DocsmigError("plan.json belongs to %s, not %s" % (plan["path"], p))
    return plan


def lock_path(run_dir, key):
    return run_dir / "locks" / (hashlib.sha1(key.encode()).hexdigest()[:16] + ".lock")


def cmd_prepare(args, run_dir):
    slug, p = resolve(args.slug)
    act = activity_map(run_dir)
    e = inventory_entry(slug, p, act)
    pr = proj_run(run_dir, slug)
    if e["mode"] == "manual" and getattr(args, "mode", None):
        g = e["git"]
        moot = ("container with nested repos", "unpushed commits on", "behind ", "legacy docs untracked but not ignored",
                "shared git dir with")
        if not e["reason"].startswith(moot):
            raise DocsmigError("--mode cannot override '%s'" % e["reason"], EXIT_MANUAL)
        if (args.mode == "git") != bool(g):
            raise DocsmigError("--mode %s does not fit (git repo: %s)" % (args.mode, bool(g)), EXIT_MANUAL)
        e["reason"] = "%s (overridden: %s, user-approved; docs stay local)" % (e["reason"], args.mode)
        e["mode"] = args.mode
    if e["mode"] in ("manual", "skip"):
        pr.mkdir(parents=True, exist_ok=True)
        (pr / "manual.txt").write_text("%s: %s\n" % (e["mode"], e["reason"]), encoding="utf-8")
        print("MANUAL %s: %s" % (slug, e["reason"]) if e["mode"] == "manual" else "SKIP %s: %s" % (slug, e["reason"]))
        return EXIT_MANUAL
    if (pr / "plan.json").exists():
        done = [f for f in ("commit.json", "applied.json", "adopt.json") if (pr / f).exists()]
        if (pr / "restored.json").exists():
            done, args.force = [], True
        if done:
            raise DocsmigError("%s already %s — restore first; refusing to discard its snapshot" % (slug, ", ".join(done)))
        if not args.force:
            raise DocsmigError("%s already prepared (use --force to redo; the old run folder is kept)" % slug)
        os.rename(str(pr), str(pr) + ".old-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    key = (e["git"] or {}).get("common_dir") or str(p)
    lk = lock_path(run_dir, key)
    lk.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(fd, ("%s %s\n" % (slug, now())).encode())
        os.close(fd)
    except FileExistsError:
        holder = lk.read_text(encoding="utf-8").strip()
        if not holder.startswith(slug + " "):
            print("MANUAL %s: locked by %s" % (slug, holder))
            return EXIT_MANUAL
    snap, out = pr / "snapshot", pr / "out"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    to_snap = set(e["legacy"]) | {r for r in e["pinned"] if not r.startswith(".claude/skills/")}
    for extra in (".gitignore", "AGENTS.md"):
        if (p / extra).is_file():
            to_snap.add(extra)
    snap_states = doc_states(p, sorted(r for r in to_snap if (p / r).is_file()), e["git"]) if e["git"] else {}
    private_all = sorted(r for r, st in snap_states.items() if st in ("ignored", "untracked")) if e["mode"] == "git" else []
    for rel in sorted(to_snap):
        src = p / rel
        if not src.is_file() or src.is_symlink():
            continue
        dst = snap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        before = sha256(src)
        shutil.copy2(src, dst)
        h = sha256(dst)
        if h != before or sha256(src) != h:
            raise DocsmigError("%s changed while snapshotting — retry" % rel, EXIT_DRIFT)
        manifest[rel] = {"sha256": h, "size": dst.stat().st_size,
                         "state": e["states"].get(rel, "pinned" if rel in e["pinned"] else "other"),
                         "class": "legacy" if rel in e["legacy"] else ("pinned" if rel in e["pinned"] else "other"),
                         "private": rel in private_all}
    gfx = e["git"] or {}
    explicit_base = ""
    if getattr(args, "base", None):
        if e["mode"] != "git":
            raise DocsmigError("--base only applies to git mode")
        explicit_base = gout(p, "rev-parse", "--verify", "--quiet", args.base + "^{commit}")
        if not explicit_base:
            raise DocsmigError("unknown base ref %s" % args.base)
        for rel, m in manifest.items():
            if m["class"] == "legacy" and m["state"] in ("tracked", "dirty"):
                at = git(p, "show", "%s:%s" % (explicit_base, rel), check=False)
                if at.returncode != 0 or hashlib.sha256(at.stdout.encode("utf-8", "surrogateescape")).hexdigest() != m["sha256"]:
                    raise DocsmigError("%s differs between %s and the working tree — --base not safe" % (rel, args.base))
    plan = {
        "slug": slug, "path": str(p), "type": e["type"], "type_evidence": e["type_evidence"], "active": e["active"],
        "mode": e["mode"], "reason": e["reason"] + (" (based on %s)" % args.base if explicit_base else ""),
        "adopt_strategy": "pull" if explicit_base else e["adopt_strategy"], "branch": BRANCH,
        "base_sha": explicit_base or gfx.get("head", ""),
        "base_branch": (args.base.split("/")[-1] if explicit_base else gfx.get("branch", "")),
        "explicit_base": bool(explicit_base), "default_ref": gfx.get("default_ref", ""),
        "lock": str(lk), "legacy": e["legacy"], "private": private_all, "pinned": e["pinned"],
        "sensitive": e["sensitive"], "allowed_slots": sorted(MATRIX[e["type"]]), "never_backfill": sorted(NEVER_BACKFILL),
        "snapshot": str(snap), "out": str(out), "ledger": str(pr / "ledger.tsv"), "keep": str(pr / "keep.tsv"),
        "created": now(),
    }
    (pr / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (pr / "plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    for f in ("ledger.tsv", "keep.tsv"):
        (pr / f).touch()
    os.chmod(pr, 0o700)
    print(json.dumps({k: plan[k] for k in ("slug", "type", "active", "mode", "reason", "adopt_strategy", "base_sha", "out")}))
    print("plan: %s" % (pr / "plan.json"))
    print("legacy (%d): %s" % (len(plan["legacy"]), ", ".join(plan["legacy"])))
    if plan["private"]:
        print("private (ignored/untracked → .local.md only): %s" % ", ".join(plan["private"]))
    if plan["sensitive"]:
        print("sensitive (never open, left in place): %s" % ", ".join(plan["sensitive"]))
    return EXIT_OK


# ----------------------------------------------------------------- verify

def out_files(out):
    return sorted(str(f.relative_to(out)) for f in Path(out).rglob("*") if f.is_file())


def load_manifest(plan):
    return json.loads((Path(plan["snapshot"]).parent / "manifest.json").read_text(encoding="utf-8"))


def parse_keep(plan):
    keep = {}
    for line in read_lines(plan["keep"]):
        if line.strip():
            cols = line.split("\t")
            keep[cols[0]] = cols[1] if len(cols) > 1 else ""
    return keep


def parse_ledger(plan):
    led = {}
    for line in read_lines(plan["ledger"]):
        if line.strip():
            cols = line.split("\t")
            if len(cols) >= 3 and cols[1].isdigit():
                led[(cols[0], int(cols[1]))] = cols[2]
    return led


def safe_rel(rel):
    return bool(rel) and not rel.startswith("/") and ".." not in Path(rel).parts


def check_reason(plan, manifest, keep, rel, lineno, text, reason, out):
    snap = Path(plan["snapshot"])
    if reason == "title":
        lines = read_lines(snap / rel)
        firsth1 = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
        return firsth1 == lineno
    if reason == "legacy-pointer":
        return is_pointer(text)
    if reason == "secret":
        return has_secret(text)
    if reason == "ai-local":  # AI-attribution line kept verbatim, but only in a local (never committed) file
        if not AI_WORDS.search(text):
            return False
        n = norm(text)
        return any(n in {norm(l) for l in read_lines(f)} for f in Path(out).rglob("*.local.md"))
    if reason == "html-comment":
        return bool(re.match(r"^\s*<!--.*-->\s*$", text))
    m = re.match(r"repoint:(.+):(\d+)$", reason)
    if m:
        f, ln = m.group(1), int(m.group(2))
        if not safe_rel(f) or not (Path(out) / f).is_file():
            return False
        lines = read_lines(Path(out) / f)
        if not 1 <= ln <= len(lines):
            return False
        src_t, dst_t = MD_TOKEN_RE.findall(text), MD_TOKEN_RE.findall(lines[ln - 1])
        if not src_t or len(src_t) != len(dst_t) or src_t == dst_t:
            return False
        if not all(d.startswith("docs/") or d in ("CLAUDE.md", "README.md") for d in dst_t):
            return False
        return norm(MD_TOKEN_RE.sub("@@", text)) == norm(MD_TOKEN_RE.sub("@@", lines[ln - 1]))
    m = re.match(r"redact-ai:(.+):(\d+)$", reason)
    if m:
        f, ln = m.group(1), int(m.group(2))
        if not safe_rel(f) or not (Path(out) / f).is_file() or not AI_WORDS.search(text):
            return False
        lines = read_lines(Path(out) / f)
        if not 1 <= ln <= len(lines) or AI_WORDS.search(lines[ln - 1]):
            return False
        lw = re.findall(r"[a-z0-9]+", norm(text).lower())
        tw = re.findall(r"[a-z0-9]+", norm(lines[ln - 1]).lower())
        it = iter(lw)
        ordered = all(any(w == x for x in it) for w in tw)  # target = legacy words in order, minus the AI mention
        return ordered and len("".join(tw)) >= 0.5 * len("".join(lw))
    m = re.match(r"(dup-of|global-dup):(.+):(\d+)$", reason)
    if not m:
        return False
    kind, f, ln = m.group(1), m.group(2), int(m.group(3))
    if kind == "dup-of":
        if not safe_rel(f):
            return False
        if (Path(out) / f).is_file():
            cand = Path(out) / f
        elif f in keep or manifest.get(f, {}).get("class") == "pinned":
            cand = snap / f  # stays in place untouched
        else:
            return False
        lines = read_lines(cand)
        return 1 <= ln <= len(lines) and norm(lines[ln - 1]) == norm(text)
    cand = Path(f).expanduser().resolve()
    allowed = [(HOME / ".claude" / n).resolve() for n in ("CLAUDE.md", "rule.md", "agent.md")] + [(WS / "CLAUDE.md").resolve()]
    if cand not in allowed and not str(cand).startswith(str((HOME / ".claude" / "references").resolve()) + "/"):
        return False
    lines = read_lines(cand)
    return 1 <= ln <= len(lines) and norm(lines[ln - 1]).lower() == norm(text).lower()


def docs_map(text):
    m = re.search(r"^## Docs map\s*$(.*?)(?=^## |\Z)", text, re.M | re.S | re.I)
    if not m:
        return None
    rows = {}
    for line in m.group(1).splitlines():
        f = re.search(r"docs/(\d\d-[A-Z-]+)(\.local)?\.md", line)
        if f and line.strip().startswith("|"):
            rows[f.group(1) + ".md"] = {"unwritten": "unwritten" in line, "local": "+local" in line or bool(f.group(2))}
    return rows


def section(text, title):
    m = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return m.group(1) if m else ""


def package_scripts(p):
    try:
        return set(json.loads((Path(p) / "package.json").read_text(encoding="utf-8")).get("scripts", {}))
    except (OSError, ValueError):
        return None


def is_ignored(p, rel):
    return git(p, "check-ignore", "-q", "--no-index", "--", rel, check=False).returncode == 0


def tracked_at(p, sha, rel):
    return bool(sha) and git(p, "cat-file", "-e", "%s:%s" % (sha, rel), check=False).returncode == 0


def classify_outputs(plan, files, manifest):
    """git mode: commit (goes into commit B) or local (placed at adopt, never committed).
    Decided by where the content comes from, never by whether the output path happens to be ignored."""
    p = Path(plan["path"])
    res = {}
    for rel in files:
        if rel.endswith(".local.md"):
            res[rel] = "local"
        elif rel in ("CLAUDE.md", "AGENTS.md") and rel in manifest:
            res[rel] = "local" if manifest[rel].get("private") else "commit"
        elif rel == "CLAUDE.md" and is_ignored(p, rel):
            res[rel] = "local"
        else:
            res[rel] = "commit"
    return res


def is_text_file(f):
    try:
        if f.is_symlink() or f.stat().st_size > 2_000_000:
            return False
        with open(f, "rb") as fh:
            return b"\0" not in fh.read(8192)
    except OSError:
        return False


def verify(plan):
    p = Path(plan["path"])
    out = Path(plan["out"])
    snap = Path(plan["snapshot"])
    fails, warns = [], []
    local_only = plan["mode"] == "git" and has_remote(p)  # localize: nothing is committed, commit-flow checks don't apply
    manifest = load_manifest(plan)
    # drift
    for rel, meta in manifest.items():
        cur = p / rel
        if meta["class"] == "legacy" and (not cur.is_file() or sha256(cur) != meta["sha256"]):
            return {"drift": True, "fails": ["drift: %s changed since prepare" % rel], "warns": [], "outputs": {}}
    files = out_files(out)
    if not files:
        return {"drift": False, "fails": ["out/ is empty"], "warns": [], "outputs": {}}
    keep = parse_keep(plan)
    for k, why in keep.items():
        if k not in plan["legacy"]:
            fails.append("keep.tsv: %s is not a legacy file" % k)
        elif not re.match(r"^(deliverable|client-facing|referenced-by:.+)$", why):
            fails.append("keep.tsv: bad reason for %s: %r" % (k, why))
        elif why.startswith("referenced-by:") and not (p / why.split(":", 1)[1]).exists():
            fails.append("keep.tsv: %s referenced-by path missing" % k)
    allowed_slots = set(plan["allowed_slots"])
    legacy_set = set(plan["legacy"])
    early_ledger = parse_ledger(plan)

    def ref_minus_ai_local(rel):
        """A ref copy may differ from its legacy source only by ai-local removals and redact-ai rewrites
        (each still verified line by line in the coverage pass)."""
        target = read_lines(out / rel)
        for srel in plan["legacy"]:
            gone = {i for (r, i), why in early_ledger.items() if r == srel and why == "ai-local"}
            repl = {}
            for (r, i), why in early_ledger.items():
                mr = re.match(r"redact-ai:(.+):(\d+)$", why)
                if r == srel and mr and mr.group(1) == rel and 1 <= int(mr.group(2)) <= len(target):
                    repl[i] = target[int(mr.group(2)) - 1]
            if not gone and not repl:
                continue
            expected = [repl.get(i, l) for i, l in enumerate(read_lines(snap / srel), 1) if i not in gone]
            if expected == target:
                return True
        return False
    snap_shas = {m["sha256"] for m in manifest.values()}
    out_text = {}
    for rel in files:
        parts = Path(rel).parts
        ok = (rel in ("CLAUDE.md", "AGENTS.md")
              or (parts[0] == "docs" and len(parts) == 2 and (parts[1] in SLOT_FILES or parts[1] in LOCAL_FILES))
              or (parts[0] == "docs" and len(parts) >= 3 and parts[1] == "ref" and rel.endswith(".md"))
              or (parts[0] == ".claude" and len(parts) == 4 and parts[1] == "skills" and parts[3] == "SKILL.md"))
        if not ok:
            fails.append("unexpected output path: %s" % rel)
            continue
        dst = p / rel
        if rel in keep:
            fails.append("%s is listed in keep.tsv — it must stay untouched, write elsewhere" % rel)
        if path_has_symlink(p, rel):
            fails.append("%s (or a parent dir) is a symlink in the project — refusing to write through it" % rel)
        elif dst.exists() and rel not in legacy_set and rel != "AGENTS.md":
            fails.append("%s already exists in the project and is not a legacy file — would be overwritten" % rel)
        if parts[0] == ".claude" and (p / ".claude" / "skills" / parts[2]).exists():
            fails.append("skill dir .claude/skills/%s already exists — pick another name" % parts[2])
        if rel.startswith("docs/ref/") and sha256(out / rel) not in snap_shas and not ref_minus_ai_local(rel):
            fails.append("%s must be a byte-identical copy of a legacy file (only ai-local lines may be removed)" % rel)
        out_text[rel] = (out / rel).read_text(encoding="utf-8", errors="replace")
    if "AGENTS.md" in files:
        orig = read_lines(snap / "AGENTS.md")
        new = read_lines(out / "AGENTS.md")
        if not orig:
            fails.append("AGENTS.md may only be modified when it already exists")
        elif new[:len(orig)] != orig:
            fails.append("AGENTS.md must keep every original line in place (append only)")
    known = set()
    for rel in manifest:
        for line in read_lines(snap / rel):
            for n in (norm(line), norm(re.sub(r"<!--|-->", " ", line))):
                if significant(n):
                    known.add(n)
    for (lrel, li), lreason in parse_ledger(plan).items():  # lines produced by a valid AI redaction count as known
        mr = re.match(r"(?:redact-ai|repoint):(.+):(\d+)$", lreason)
        src = read_lines(snap / lrel) if lrel in manifest else []
        if mr and 1 <= li <= len(src) and check_reason(plan, manifest, keep, lrel, li, src[li - 1], lreason, out):
            known.add(norm(read_lines(out / mr.group(1))[int(mr.group(2)) - 1]))
    tdir = Path(__file__).resolve().parent.parent / "templates"
    for t in (tdir.glob("*.md") if tdir.is_dir() else []):
        for line in read_lines(t):
            if line.startswith("#"):
                known.add(norm(line))

    def new_text_check(rel, lines, slot_no=None):
        sections, cur = [], []
        for l in lines:
            if l.startswith("#") and cur:
                sections.append(cur)
                cur = []
            cur.append(l)
        if cur:
            sections.append(cur)
        for sec in sections:
            new, srcs = [], []
            for l in sec:
                nl = norm(re.sub(r"<!--|-->", " ", l))
                if nl.startswith("Source:"):
                    srcs.append(l)
                    continue
                if not significant(nl) or l.lstrip().startswith(("#", "|---", "|:--")) or nl in known or is_pointer(l):
                    continue
                if re.search(r"`\.claude/skills/[^`/]+/SKILL\.md`", l):
                    continue  # project-skills index line in 06-AGENTS
                new.append(nl)
            valid_src = False
            for s in srcs:
                if norm(s) in known:
                    continue  # a verbatim legacy "Source:" line is not a citation this migration made
                paths = re.findall(r"`([^`]+)`", s)
                if not paths:
                    fails.append("%s: Source line without a `path`: %s" % (rel, norm(s)[:80]))
                for path in paths:
                    pp = path.split(":")[0].split("#")[0]
                    if not safe_rel(pp) or not (p / pp).exists():
                        fails.append("%s: Source path does not exist: %s" % (rel, path))
                    else:
                        valid_src = True
                if norm(s) not in known and slot_no is not None:
                    if slot_no in NEVER_BACKFILL:
                        fails.append("%s: slot %02d is never written from code" % (rel, slot_no))
                    if slot_no not in allowed_slots:
                        fails.append("%s: backfill outside the %s type matrix" % (rel, plan["type"]))
            if new and not valid_src:
                fails.append("%s: unsourced new text (keep legacy wording or cite `Source: path`): %s" % (rel, new[0][:100]))

    slot_present = {}
    for rel, text in out_text.items():
        parts = Path(rel).parts
        lines = text.splitlines()
        if "<!-- GUIDE" in text or any(re.search(r"\bTBD\b", l) and norm(l) not in known for l in lines):
            fails.append("%s: template guide comment or new TBD text left in" % rel)
        if parts[0] == ".claude":
            body = text.split("\n---", 1)[1] if text.startswith("---") and "\n---" in text else text
            new_text_check(rel, body.splitlines())
            continue
        if parts[0] != "docs" or len(parts) != 2:
            continue
        name = parts[1]
        n = SLOT_FILES.get(name) or LOCAL_FILES.get(name)
        slot_present.setdefault(n, set()).add(name)
        real = [l for l in lines if significant(norm(l)) and not l.lstrip().startswith(("#", "<!--", "|---"))]
        migrated = [l for l in real if norm(l) in known]
        if not real or (len(real) < 3 and not migrated):
            fails.append("%s: placeholder (fewer than 3 real lines and no migrated content)" % rel)
        if len(lines) > 300:
            warns.append("%s: %d lines (>300) — move verbatim material to docs/ref/" % (rel, len(lines)))
        if n not in allowed_slots:
            warns.append("%s: slot outside the %s type matrix" % (rel, plan["type"]))
        new_text_check(rel, lines, n)
    alltext = "\n".join(t for r, t in out_text.items() if not r.startswith("docs/ref/"))
    for rel in files:
        if rel.startswith("docs/ref/") and rel not in alltext and rel[5:] not in alltext:
            fails.append("%s is not linked from any doc" % rel)
    # CLAUDE.md
    ctext = out_text.get("CLAUDE.md")
    if ctext is None:
        fails.append("CLAUDE.md missing from out/")
    else:
        cl = ctext.splitlines()
        if len(cl) > 100:
            fails.append("CLAUDE.md: %d lines (>100)" % len(cl))
        elif len(cl) > 70:
            warns.append("CLAUDE.md: %d lines (>70 target)" % len(cl))
        if any(re.match(r"^\s*@\S", l) and l.strip() != "@AGENTS.md" for l in cl):
            fails.append("CLAUDE.md: @ import found (only `@AGENTS.md` is allowed)")
        if "GUIDE" in ctext or "<One line" in ctext or "<rule>" in ctext:
            fails.append("CLAUDE.md: template placeholders left in")
        csecs, title, pre_new, seen_h1 = {}, None, [], False
        for l in cl:
            if l.startswith("# ") and not seen_h1:
                seen_h1 = True
                continue
            m2 = re.match(r"^##\s+(.+?)\s*$", l)
            if m2:
                title = m2.group(1).strip().lower()
                csecs.setdefault(title, [])
                continue
            nl = norm(re.sub(r"<!--|-->", " ", l))
            if not significant(nl) or nl in known:
                continue
            if title is None:
                pre_new.append(nl)
            else:
                csecs[title].append((l, nl))
        if len(pre_new) > 1:
            fails.append("CLAUDE.md: only one new identity line is allowed before the first section (got %d)" % len(pre_new))
        for t, items in csecs.items():
            for l, nl in items:
                if t == "hard rules":
                    fails.append("CLAUDE.md Hard rules must be verbatim legacy rules: %s" % nl[:90])
                elif t in ("stack", "commands"):
                    warns.append("CLAUDE.md %s line is new text (check it): %s" % (t, nl[:90]))
                elif t == "docs map":
                    if not (l.lstrip().startswith("|") or nl.startswith(("N/A", "Open only what"))):
                        fails.append("CLAUDE.md Docs map: unexpected text: %s" % nl[:90])
                else:
                    fails.append("CLAUDE.md section '%s' has new text (only Hard rules/Stack/Commands/Docs map may): %s"
                                 % (t, nl[:80]))
        dm = docs_map(ctext)
        if dm is None:
            fails.append("CLAUDE.md: no '## Docs map' section")
        else:
            for name, n in SLOT_FILES.items():
                present = name in slot_present.get(n, set())
                localp = ("%02d-%s.local.md" % (n, SLOTS[n])) in slot_present.get(n, set())
                row = dm.get(name)
                if (present or localp) and (row is None or row["unwritten"]):
                    fails.append("Docs map: %s exists but row missing or marked unwritten" % name)
                if row and not row["unwritten"] and not (present or localp):
                    fails.append("Docs map: %s listed but no file (mark it unwritten)" % name)
                if row and row["local"] != localp:
                    fails.append("Docs map: %s +local marker does not match .local.md presence" % name)
                if row is None and n in allowed_slots and not present:
                    warns.append("Docs map: applicable slot %s has no row (add it as unwritten)" % name)
        scripts = package_scripts(p)
        if scripts is not None:
            for cmd in re.findall(r"`((?:npm|pnpm|yarn|bun) [^`]+)`", ctext):
                toks = cmd.split()
                name = toks[2] if len(toks) > 2 and toks[1] == "run" else toks[1]
                if name not in scripts and name not in ("install", "i", "ci", "test", "start", "add", "dlx", "exec", "x"):
                    fails.append("CLAUDE.md: command not in package.json scripts: %s" % cmd)
    # coverage + ledger (git mode: tracked legacy content must land in a committed output)
    led = parse_ledger(plan)
    out_norm = set()
    for rel in files:
        for l in read_lines(out / rel):
            out_norm.add(norm(l))
    committed_norm = None
    if plan["mode"] == "git" and not local_only:
        committed_norm = set()
        pre_outputs = classify_outputs(plan, files, manifest)
        for rel, kind in pre_outputs.items():
            if kind == "commit":
                for l in read_lines(out / rel):
                    committed_norm.add(norm(l))
    left_git = []
    uncovered, secrets_dropped = [], 0
    for rel in plan["legacy"]:
        if rel in keep or rel not in manifest:
            continue
        tracked_src = committed_norm is not None and manifest[rel]["state"] in ("tracked", "dirty")
        for i, line in enumerate(read_lines(snap / rel), 1):
            n_ = norm(line)
            if not significant(n_):
                continue
            if n_ in out_norm and not (tracked_src and n_ not in committed_norm):
                continue
            if n_ in out_norm and tracked_src and (rel, i) not in led:
                left_git.append("%s:%d: %s" % (rel, i, n_[:90]))
                continue
            reason = led.get((rel, i))
            if not reason:
                uncovered.append("%s:%d: %s" % (rel, i, n_[:110]))
            elif not check_reason(plan, manifest, keep, rel, i, line, reason, out):
                fails.append("ledger: reason %r does not hold for %s:%d" % (reason, rel, i))
            elif reason == "secret":
                secrets_dropped += 1
    if uncovered:
        fails.append("coverage: %d legacy lines not in out/ and not in ledger.tsv (first: %s)"
                     % (len(uncovered), uncovered[0]))
    if left_git:
        fails.append("tracked content would leave git: %d line(s) from committed files land only in local outputs "
                     "(first: %s) — keep them in a committed slot or handle the project manually" % (len(left_git), left_git[0]))
    (Path(plan["snapshot"]).parent / "uncovered.txt").write_text("\n".join(uncovered) + "\n", encoding="utf-8")
    if secrets_dropped:
        warns.append("%d secret line(s) dropped — move them into the vault (they remain only in the snapshot)" % secrets_dropped)
    # outputs: commit vs local, privacy
    outputs = {}
    gitrepo = git_facts(p) is not None
    if local_only:
        outputs = {rel: "local" for rel in files}
    elif plan["mode"] == "git":
        outputs = classify_outputs(plan, files, manifest)
        for rel, kind in outputs.items():
            if rel.endswith(".local.md") and not is_ignored(p, rel):
                fails.append("%s is not gitignored (add *.local.md to the global ignore)" % rel)
            elif kind == "commit" and is_ignored(p, rel) and not tracked_at(p, plan["base_sha"], rel):
                fails.append("%s would be committed (its content is tracked today) but the path is gitignored "
                             "— handle this project manually" % rel)
        pub_lines = set()
        for rel, m in manifest.items():
            if not m.get("private"):
                pub_lines |= {norm(l) for l in read_lines(snap / rel)}
        priv = {norm(l) for rel, m in manifest.items() if m.get("private")
                for l in read_lines(snap / rel) if significant(norm(l))} - pub_lines
        for rel, kind in outputs.items():
            if kind != "commit":
                continue
            for l in read_lines(out / rel):
                if norm(l) in priv:
                    fails.append("privacy: %s would commit a line from an ignored/untracked source (use .local.md): %s"
                                 % (rel, norm(l)[:80]))
                    break
        for rel, m in manifest.items():
            if m["class"] == "legacy" and m["state"] == "dirty":
                at_base = set(git(p, "show", "%s:%s" % (plan["base_sha"], rel), check=False).stdout.splitlines())
                fresh = [l for l in read_lines(snap / rel) if has_secret(l) and l not in at_base]
                if fresh:  # secrets already committed at base add no new exposure; only new ones block commit A
                    fails.append("secret in uncommitted edits of %s — vault it before migrating (commit A would record it)" % rel)
    elif gitrepo and plan["mode"] != "git":
        for rel in files:
            if not is_ignored(p, rel) and not tracked_at(p, plan["base_sha"] or "HEAD", rel):
                fails.append("local-only repo: %s would not be gitignored" % rel)
    # secrets in outputs
    for rel in files:
        for i, l in enumerate(read_lines(out / rel), 1):
            if has_secret(l):
                (warns if rel.endswith(".local.md") else fails).append("secret pattern in %s:%d" % (rel, i))
    # dangling references to files that will be deleted
    deleting = [r for r in plan["legacy"] if r not in keep and r != "CLAUDE.md" and r not in files]
    if deleting:
        names = {Path(r).name for r in deleting}
        for f in walk_files(p, max_depth=6):
            try:
                rel = str(f.relative_to(p))
                if (rel in manifest or is_sensitive(f.name) or f.name.lower().startswith(".env")
                        or any(f.name.lower().endswith(s) for s in TEXT_SUFFIXES_SKIP) or not is_text_file(f)):
                    continue
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hit = sorted(n for n in names if re.search(r"(?<![\w-])" + re.escape(n) + r"\b", txt))
            if hit:
                hit_lines = [l for l in txt.splitlines() if any(re.search(r"(?<![\w-])" + re.escape(n) + r"\b", l) for n in hit)]
                if f.name.lower().endswith("ignore") or all("exclude" in l.lower() for l in hit_lines):
                    warns.append("%s lists %s in an ignore/exclude list — update it after migration" % (rel, ", ".join(hit)))
                elif (not [n for n in hit if re.search(r"(?<![\w-])" + re.escape(n) + r"\b", BLOCK_COMMENT_RE.sub(" ", txt))]
                      or all(l.strip().startswith(COMMENT_PREFIXES) for l in hit_lines)):
                    warns.append("%s mentions %s in a comment — update the comment after adoption" % (rel, ", ".join(hit)))
                elif f.suffix.lower() == ".md":
                    warns.append("%s mentions %s (doc text, not code)" % (rel, ", ".join(hit)))
                else:
                    fails.append("code/config %s references %s — keep it (keep.tsv referenced-by:%s) or update the code"
                                 % (rel, ", ".join(hit), rel))
    # deploy uploads of the project root
    has_local = any(r.endswith(".local.md") for r in files) or any(k == "local" for k in outputs.values())
    blockers = deploy_blockers(p, has_local, {Path(r).name for r in plan["legacy"]})
    if local_only:  # CI checks out tracked files only — local docs never reach a workflow
        blockers = [x for x in blockers if not re.match(r"\.github/workflows/[^/]+\.ya?ml$", x[0])]
    for brel, why in blockers:
        warns.append("DEPLOY BLOCKER %s: %s — fix it before adopt/apply (they refuse until then)" % (brel, why))
    for drel in deploy_scripts(p):
        if local_only and re.match(r"\.github/workflows/[^/]+\.ya?ml$", drel):
            continue
        if drel not in dict(blockers) and not re.search(r"exclude[^\n]*(docs|\*\.md|\.local\.md|CLAUDE)",
                                                        (p / drel).read_text(encoding="utf-8", errors="ignore")):
            warns.append("deploy script %s uploads files without excluding docs/ — list deploy excludes in 16" % drel)
    return {"drift": False, "fails": sorted(set(fails)), "warns": sorted(set(warns)), "outputs": outputs,
            "deploy_blockers": blockers}


def read_text_safe(f):
    try:
        return Path(f).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def deploy_scripts(p):
    res = []
    for f in walk_files(p, max_depth=3):
        if f.suffix in (".sh", ".yml", ".yaml") or f.name in ("package.json", "Makefile"):
            try:
                if re.search(r"\b(rsync|scp|lftp|sftp)\b", f.read_text(encoding="utf-8", errors="ignore")):
                    res.append(str(f.relative_to(p)))
            except OSError:
                pass
    return res


ROOT_SRC_RE = re.compile(r"(?:^|\s)(?:\./?|\*|\$\{?PWD\}?/?|\$\(pwd\)/?|\"\$\{?(?:ROOT|PROJECT_ROOT|APP_ROOT|DIR|SRC)\}?/?\")(?:\s|$)")


UPLOAD_TOOLS = ("rsync", "scp", "lftp", "sftp")
VALUE_OPTS = {  # options whose value is the next argument (per tool: `-c`/`-u` are flags in rsync, values in scp)
    "rsync": {"--exclude", "--exclude-from", "--include", "--include-from", "--filter", "-f", "-e", "--rsh", "--chown",
              "--chmod", "--port", "--log-file", "--rsync-path", "--password-file", "--temp-dir", "-T", "--partial-dir",
              "--backup-dir", "--suffix", "--compare-dest", "--link-dest", "--copy-dest", "--files-from", "-M",
              "--remote-option", "--usermap", "--groupmap", "--out-format", "--timeout", "--contimeout", "--bwlimit",
              "--max-size", "--min-size", "--modify-window", "--iconv", "--info", "--debug", "--address"},
    "scp": {"-i", "-P", "-o", "-F", "-l", "-c", "-S", "-J", "-D", "-X"},
}
ROOT_ARG_RE = re.compile(r"^(?:\.|\./|\*|\$\{?PWD\}?/?|\$\(pwd\)/?|\$\{?(?:ROOT|PROJECT_ROOT|APP_ROOT|DIR|SRC)\}?/?)$")


def rsync_glob(pat):
    """rsync wildcard -> regex: `*` and `?` stop at `/`, `**` crosses it."""
    out, i = "", 0
    while i < len(pat):
        c = pat[i]
        if pat.startswith("**", i):
            out += ".*"
            i += 2
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[" and pat.find("]", i + 1) > i:
            j = pat.find("]", i + 1)
            cls = pat[i + 1:j]
            cls = "^" + cls[1:] if cls.startswith("!") else cls
            out += "[" + cls.replace("\\", "\\\\") + "]"
            i = j
        else:
            out += re.escape(c)
        i += 1
    return re.compile(out + r"\Z")


def rsync_excludes(path, pats):
    """True when an rsync exclude in pats keeps `path` (relative to the transfer root) off the destination."""
    parts = path.split("/")
    for raw in pats:
        pat = raw.strip()
        if not pat:
            continue
        anchored = pat.startswith("/")
        body = pat.lstrip("/")
        dir_only = body.endswith("/")
        body = body.rstrip("/")
        if not body:
            continue
        rx = rsync_glob(body)
        depth = body.count("/") + 1
        for i in range(1, len(parts) + 1):
            if dir_only and i == len(parts):
                continue  # a trailing slash only matches directories
            if anchored:
                if i == depth and rx.match("/".join(parts[:i])):
                    return True
            elif "/" in body or "**" in body:
                if "**" in body:
                    if rx.match("/".join(parts[:i])):
                        return True
                elif i >= depth and rx.match("/".join(parts[i - depth:i])):
                    return True
            elif rx.match(parts[i - 1]):
                return True
    return False


def upload_commands(p, rel, txt):
    """(tool, argv) of every rsync/scp/lftp/sftp call in a deploy file: continuations folded, comments dropped,
    package.json scripts read as commands."""
    lines = []
    if rel.endswith("package.json"):
        try:
            lines = list((json.loads(txt).get("scripts") or {}).values())
        except ValueError:
            lines = txt.splitlines()
    else:
        lines = re.sub(r"\\\s*\n", " ", txt).splitlines()
    cmds = []
    for line in lines:
        s = re.sub(r"^\s*(?:-\s*)?(?:run:\s*)?[@-]?", "", line).strip()
        if not s or s.startswith("#") or not re.search(r"\b(rsync|scp|lftp|sftp)\b", s):
            continue
        for part in re.split(r"\s*(?:&&|\|\||;|\|)\s*", s):
            try:
                argv = shlex.split(part, comments=True)
            except ValueError:
                argv = part.split()
            while argv and (re.match(r"^\w+=", argv[0]) or argv[0] in ("sudo", "exec", "command", "nohup", "time", "env")):
                argv = argv[1:]
            if argv and os.path.basename(argv[0]) in UPLOAD_TOOLS:
                cmds.append((os.path.basename(argv[0]), argv[1:]))
    return cmds


def exclude_patterns(p, rel, argv):
    pats, i = [], 0

    def from_file(f):
        for base in ((p / rel).parent, p):
            t = read_text_safe(base / f)
            if t:
                return [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith(("#", ";"))]
        return []
    while i < len(argv):
        a = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else ""
        if a.startswith("--exclude="):
            pats.append(a.split("=", 1)[1])
        elif a == "--exclude":
            pats.append(nxt)
            i += 1
        elif a.startswith("--exclude-from="):
            pats += from_file(a.split("=", 1)[1])
        elif a == "--exclude-from":
            pats += from_file(nxt)
            i += 1
        elif a.startswith("--filter=") or a in ("--filter", "-f"):
            rule = a.split("=", 1)[1] if "=" in a else nxt
            if a in ("--filter", "-f"):
                i += 1
            m = re.match(r"^(?:-|exclude)[ ,_]+(.+)$", rule.strip())
            if m:
                pats.append(m.group(1))
        i += 1
    return pats


def upload_sources(tool, argv):
    """(sources, uses --files-from). lftp/sftp carry their sources inside script strings: treated as the root."""
    if tool in ("lftp", "sftp"):
        return ["."], False
    pos, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_OPTS.get(tool, ()):
            i += 2
            continue
        if not a.startswith("-"):
            pos.append(a)
        i += 1
    return pos[:-1], any(a == "--files-from" or a.startswith("--files-from=") for a in argv)


def deploy_blockers(p, has_local, legacy_names, need_claude_dir=False):
    """Deploy files whose upload command sends the project root while a local doc would ship with it. Each
    rsync call is parsed on its own (its own --exclude / --exclude-from / --filter values) and the real doc paths
    are tested against them with rsync's matching rules; scp/lftp/sftp have no excludes. Fails closed."""
    must = ([INDEX_LOCAL, "docs/02-DESIGN.md", "docs/07-README.local.md", AGENTS_LOCAL] if need_claude_dir
            else ["CLAUDE.md", "docs/02-DESIGN.md", "docs/07-README.local.md"])
    out = []
    for rel in deploy_scripts(p):
        txt = (p / rel).read_text(encoding="utf-8", errors="ignore")
        for tool, argv in upload_commands(p, rel, txt):
            srcs, listed = upload_sources(tool, argv)
            pats = exclude_patterns(p, rel, argv) if tool == "rsync" else []
            excluded_legacy = sorted(n for n in legacy_names if any(rsync_excludes(n, [x]) for x in pats))
            if listed or not (any(ROOT_ARG_RE.match(s) for s in srcs) or excluded_legacy):
                continue  # uploads named files/subfolders only (themes/, dist/…), never the project tree
            need = must + (["AGENTS.md"] if any(a in ("-L", "--copy-links") or re.match(r"^-[A-Za-z]*L", a) for a in argv)
                           else [])
            leak = [m for m in need if not rsync_excludes(m, pats)]
            if leak:
                out.append((rel, "%s uploads the project root and would ship %s%s" % (
                    tool, ", ".join(leak), " (it already excludes %s)" % ", ".join(excluded_legacy)
                    if excluded_legacy else "")))
                break
    return out


def report_verify(res, plan):
    pr = Path(plan["snapshot"]).parent
    (pr / "verify.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for f in res["fails"]:
        print("FAIL " + f)
    for w in res["warns"]:
        print("WARN " + w)
    if res.get("drift"):
        return EXIT_DRIFT
    print("verify: %s (%d fail, %d warn)" % ("OK" if not res["fails"] else "FAILED", len(res["fails"]), len(res["warns"])))
    return EXIT_OK if not res["fails"] else EXIT_FAIL


def cmd_verify(args, run_dir):
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    return report_verify(verify(plan), plan)


# ----------------------------------------------------------------- commit / apply / adopt / restore

def release_lock(plan):
    try:
        Path(plan["lock"]).unlink()
    except (FileNotFoundError, KeyError):
        pass


def cmd_commit(args, run_dir):
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    if plan["mode"] != "git":
        raise DocsmigError("%s is mode %s — use apply" % (slug, plan["mode"]))
    if has_remote(p):
        print("MANUAL: %s has a git remote — project docs are local-only; use localize, not commit" % slug)
        return EXIT_MANUAL
    res = verify(plan)
    rc = report_verify(res, plan)
    if rc != EXIT_OK:
        return rc
    if not plan.get("explicit_base") and gout(p, "rev-parse", "HEAD") != plan["base_sha"]:
        print("drift: HEAD moved since prepare")
        return EXIT_DRIFT
    if git(p, "show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH, check=False).returncode == 0:
        print("MANUAL: branch %s already exists" % BRANCH)
        return EXIT_MANUAL
    manifest = load_manifest(plan)
    keep = parse_keep(plan)
    out, snap = Path(plan["out"]), Path(plan["snapshot"])
    commit_outputs = [r for r, k in res["outputs"].items() if k == "commit"]
    tmpdir = tempfile.mkdtemp(prefix="docsmig-")
    idx = os.path.join(tmpdir, "index")
    ix = {"GIT_INDEX_FILE": idx}
    sha_a = sha_b = ""
    try:
        git(p, "read-tree", plan["base_sha"], env_extra=ix)
        parent = plan["base_sha"]
        dirty = [r for r, m in manifest.items() if m["class"] == "legacy" and m["state"] == "dirty"]
        if dirty:
            for rel in dirty:
                mode = (gout(p, "ls-files", "-s", "--", rel).split() or ["100644"])[0]
                blob = gout(p, "hash-object", "-w", "--path=" + rel, str(snap / rel))
                git(p, "update-index", "--add", "--cacheinfo", "%s,%s,%s" % (mode, blob, rel), env_extra=ix)
            tree = gout(p, "write-tree", env_extra=ix)
            sha_a = gout(p, "commit-tree", tree, "-p", parent, "-m", "docs: commit in-progress project notes")
            parent = sha_a
        for rel, m in manifest.items():
            if m["class"] == "legacy" and rel not in keep and m["state"] in ("tracked", "dirty") and rel not in commit_outputs:
                git(p, "update-index", "--force-remove", "--", rel, env_extra=ix)
        for rel in commit_outputs:
            blob = gout(p, "hash-object", "-w", "--path=" + rel, str(out / rel))
            git(p, "update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel), env_extra=ix)
        tree = gout(p, "write-tree", env_extra=ix)
        if tree == gout(p, "rev-parse", (sha_a or plan["base_sha"]) + "^{tree}"):
            raise DocsmigError("nothing to commit — every output is gitignored (local-only); use in-place handling",
                               EXIT_MANUAL)
        msg = "docs: restructure project docs into numbered slots"
        if AI_WORDS.search(msg):
            raise DocsmigError("commit message contains AI attribution")
        sha_b = gout(p, "commit-tree", tree, "-p", parent, "-m", msg)
        if not sha_b:
            raise DocsmigError("commit-tree failed")
        git(p, "update-ref", "refs/heads/" + BRANCH, sha_b, "")  # empty old value = must not exist yet
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    changed = gz(p, "diff", "-z", "--no-renames", "--name-only", plan["base_sha"], sha_b, "--")
    allowed = set(commit_outputs) | {r for r in manifest if manifest[r]["class"] == "legacy"}
    stray = [c for c in changed if c not in allowed]
    if stray:
        git(p, "update-ref", "-d", "refs/heads/" + BRANCH, sha_b)
        raise DocsmigError("commit touched unexpected paths %s — branch removed" % stray, EXIT_FAIL)
    rec = {"base": plan["base_sha"], "commit_a": sha_a, "commit_b": sha_b, "branch": BRANCH, "files": changed,
           "commit_outputs": commit_outputs, "local_outputs": [r for r, k in res["outputs"].items() if k == "local"],
           "time": now()}
    (Path(plan["snapshot"]).parent / "commit.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    release_lock(plan)
    print("committed %s@%s (A=%s) — %d paths; checkout untouched, nothing pushed"
          % (BRANCH, sha_b[:10], sha_a[:10] or "-", len(changed)))
    return EXIT_OK


def cmd_apply(args, run_dir):
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    if plan["mode"] != "in-place":
        raise DocsmigError("%s is mode %s — use commit" % (slug, plan["mode"]))
    pr = Path(plan["snapshot"]).parent
    if (pr / "applied.json").exists():
        raise DocsmigError("%s already applied" % slug)
    res = verify(plan)
    rc = report_verify(res, plan)
    if rc != EXIT_OK:
        return rc
    if res.get("deploy_blockers"):
        print("MANUAL: deploy blocker(s) %s — fix the deploy excludes first" % [b[0] for b in res["deploy_blockers"]])
        return EXIT_MANUAL
    manifest = load_manifest(plan)
    keep = parse_keep(plan)
    out = Path(plan["out"])
    files = out_files(out)
    nested = [rel for rel in files if in_nested_repo(p, rel)]
    if nested:
        print("MANUAL: %s would land inside a nested repo — it could be pushed from there" % nested[:4])
        return EXIT_MANUAL
    for rel in files:
        dst = p / rel
        if path_has_symlink(p, rel) or (dst.exists() and (rel not in manifest or sha256(dst) != manifest[rel]["sha256"])):
            raise DocsmigError("refusing to overwrite %s (symlink, not snapshotted or changed since prepare)" % rel, EXIT_DRIFT)
    copied, deleted = [], []
    for rel in files:
        safe_copy(out / rel, p / rel, root=p)
        copied.append({"path": rel, "sha256": sha256(p / rel)})
    for rel, m in manifest.items():
        if m["class"] != "legacy" or rel in keep or rel in files:
            continue
        cur = p / rel
        if cur.is_file() and not cur.is_symlink() and sha256(cur) == m["sha256"]:
            cur.unlink()
            deleted.append(rel)
            d = cur.parent
            while d != p and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
    rec = {"copied": copied, "deleted": deleted, "time": now()}
    (pr / "applied.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    release_lock(plan)
    print("applied %s: %d files written, %d legacy files removed (snapshot kept)" % (slug, len(copied), len(deleted)))
    return EXIT_OK


def worktree_changes(p, paths):
    """Paths among `paths` with staged/unstaged changes or an untracked file present."""
    if not paths:
        return []
    return [e[3:] for e in gz(p, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames", "--", *paths)
            if len(e) > 3]


def cmd_adopt(args, run_dir):
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    pr = Path(plan["snapshot"]).parent
    if has_remote(p):
        print("MANUAL: %s has a git remote — project docs are local-only; use localize, not adopt" % slug)
        return EXIT_MANUAL
    if not (pr / "commit.json").exists():
        raise DocsmigError("nothing to adopt for %s (no commit.json)" % slug)
    if (pr / "adopt.json").exists():
        raise DocsmigError("%s already adopted" % slug)
    rec = json.loads((pr / "commit.json").read_text(encoding="utf-8"))
    manifest = load_manifest(plan)
    keep = parse_keep(plan)
    out = Path(plan["out"])
    planned = plan.get("adopt_strategy") or "ff"
    strategy = args.strategy or planned
    if strategy != planned:
        raise DocsmigError("%s was planned for '%s' adoption (%s) — refusing '%s'"
                           % (slug, planned, plan["reason"], strategy), EXIT_MANUAL)
    gf = git_facts(p)
    pre = gout(p, "rev-parse", "HEAD")
    dirty_legacy = [r for r, m in manifest.items() if m["class"] == "legacy" and m["state"] == "dirty"]
    # ---- preconditions (nothing is changed until all pass)
    blk = deploy_blockers(p, bool(rec.get("local_outputs")), {Path(r).name for r in plan["legacy"]})
    if blk:
        print("MANUAL: deploy blocker(s) %s — fix the deploy excludes first" % [b[0] for b in blk])
        return EXIT_MANUAL
    if gf["in_progress"]:
        print("MANUAL: git operation in progress (%s)" % gf["in_progress"])
        return EXIT_MANUAL
    if strategy == "ff":
        tip = gout(p, "rev-parse", "--verify", "--quiet", "refs/heads/" + BRANCH)
        if tip != rec["commit_b"]:
            print("drift: %s is %s, expected %s" % (BRANCH, tip[:10] or "missing", rec["commit_b"][:10]))
            return EXIT_DRIFT
        if gf["branch"] != plan["base_branch"] or pre != plan["base_sha"]:
            print("drift: checkout is %s@%s, prepared on %s@%s" % (gf["branch"], pre[:10], plan["base_branch"], plan["base_sha"][:10]))
            return EXIT_DRIFT
        if git(p, "diff", "--cached", "--quiet", check=False).returncode != 0:
            print("MANUAL: staged changes in the index — commit or unstage them first")
            return EXIT_MANUAL
        for rel in dirty_legacy:
            if not (p / rel).is_file() or sha256(p / rel) != manifest[rel]["sha256"]:
                print("drift: %s changed since prepare" % rel)
                return EXIT_DRIFT
        busy = [r for r in worktree_changes(p, rec["files"]) if r not in dirty_legacy and r not in manifest]
        if busy:
            print("MANUAL: uncommitted or untracked files on paths the docs commit touches: %s" % busy[:5])
            return EXIT_MANUAL
        for rel in rec["files"]:  # an ignored local file at an incoming path would be silently overwritten by git
            f = p / rel
            if (f.exists() or f.is_symlink()) and not tracked_at(p, "HEAD", rel) and rel not in manifest:
                print("MANUAL: local untracked/ignored file would be overwritten by the docs commit: %s" % rel)
                return EXIT_MANUAL
            if rel in manifest and f.exists() and not tracked_at(p, "HEAD", rel) and sha256(f) != manifest[rel]["sha256"]:
                print("drift: %s changed since prepare" % rel)
                return EXIT_DRIFT
    else:
        landed = git(p, "merge-base", "--is-ancestor", rec["commit_b"], "HEAD", check=False).returncode == 0
        if not landed:
            missing = [r for r in rec["commit_outputs"] if not tracked_at(p, "HEAD", r)]
            still = [r for r in rec["files"] if r not in rec["commit_outputs"] and tracked_at(p, "HEAD", r)]
            if missing or still:
                print("not landed yet (missing %d slot files, %d legacy files still tracked) — merge the PR and pull first"
                      % (len(missing), len(still)))
                return EXIT_MANUAL
    local_outputs = [r for r in out_files(out) if r in rec["local_outputs"]]
    for rel in local_outputs:
        dst = p / rel
        if dst.is_symlink() or (dst.exists() and (rel not in manifest or sha256(dst) != manifest[rel]["sha256"])):
            print("MANUAL: %s already exists locally and differs — move it aside first" % rel)
            return EXIT_MANUAL
    # ---- act
    backup = pr / "pre-adopt"
    if strategy == "ff":
        for rel in dirty_legacy:
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p / rel, backup / rel)
        if dirty_legacy:
            git(p, "checkout", "--", *dirty_legacy)  # their bytes are in commit A and in pre-adopt/
        untracked_private = [r for r, m in manifest.items() if m["class"] == "legacy" and m["state"] == "untracked"
                             and r in rec["files"]]
        for rel in untracked_private:  # would block the merge; content is preserved in the snapshot/.local.md
            stash_to(backup, rel, p / rel)
        r = git(p, "merge", "--ff-only", BRANCH, check=False)
        if r.returncode != 0:
            for rel in dirty_legacy + untracked_private:
                shutil.copy2(backup / rel, p / rel)
            print("MANUAL: fast-forward failed (%s) — working tree restored" % r.stderr.strip()[:200])
            return EXIT_MANUAL
        git(p, "update-ref", "-d", "refs/heads/" + BRANCH, rec["commit_b"], check=False)
    else:
        if git(p, "show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH, check=False).returncode == 0:
            git(p, "update-ref", "-d", "refs/heads/" + BRANCH, rec["commit_b"], check=False)
    placed = []
    for rel in local_outputs:
        safe_copy(out / rel, p / rel, root=p)
        placed.append({"path": rel, "sha256": sha256(p / rel)})
    removed = []
    for rel, m in manifest.items():
        if m["class"] == "legacy" and rel not in keep and m["state"] in ("ignored", "untracked"):
            cur = p / rel
            if cur.is_file() and not cur.is_symlink() and sha256(cur) == m["sha256"]:
                cur.unlink()
                removed.append(rel)
    (pr / "adopt.json").write_text(json.dumps({"strategy": strategy, "branch": gf["branch"], "pre_adopt": pre,
                                               "adopted_tip": gout(p, "rev-parse", "HEAD"), "local_placed": placed,
                                               "removed": removed, "time": now()}, indent=1), encoding="utf-8")
    print("adopted %s (%s): %d local file(s) placed, %d local legacy file(s) removed; nothing pushed"
          % (slug, strategy, len(placed), len(removed)))
    return EXIT_OK


# ----------------------------------------------------------------- localize (project docs never leave this machine)

LOCALIZE_MSG = "docs: stop tracking internal project docs"
INDEX_LOCAL = ".claude/CLAUDE.md"  # the index in a repo with a remote: loaded exactly like ./CLAUDE.md (project memory),
#                                    and no commit tracks this path, so git never overwrites or deletes it
AGENTS_LOCAL = "AGENTS.local.md"   # AGENTS.md becomes a link to it: a checkout may remove the link, never the content
DISK_NAME = {"CLAUDE.md": INDEX_LOCAL, "AGENTS.md": AGENTS_LOCAL}
EXCLUDE_MARK = b"# project docs stay on this machine (docs/01-17 standard): never commit them"
EXCLUDE_LINES = [b"/CLAUDE.md", b"/.claude/CLAUDE.md", b"/CLAUDE.local.md", b"/AGENTS.md", b"/AGENTS.local.md",
                 b"/docs/[0-9][0-9]-*.md", b"/docs/ref/", b"/.claude/skills/", b"*.local.md"]
LITERAL = {"GIT_LITERAL_PATHSPECS": "1"}
MIRROR_ROOT = Path(os.environ.get("DOCSMIG_MIRROR") or WS / "_backups" / "local-docs")  # copies, outside any work tree
LOCK_ROOT = Path(os.environ.get("DOCSMIG_LOCKS") or WS / "_backups" / "locks")  # stable across run dirs


def mirror_dir(p):
    """Keyed by the absolute path, so two repos with the same folder name never share a mirror."""
    return MIRROR_ROOT / slug_dir(str(Path(p).resolve()))


def mirror_put(m, rel, src):
    """Copy src to the mirror; an older, different copy is kept under .history/ (last 5 per file), never lost."""
    dst = m / rel
    if dst.is_file() and sha256(dst) == sha256(src):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file():
        hist = m / ".history" / rel
        hist.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dst), str(hist.with_name(hist.name + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))))
        old = sorted(hist.parent.glob(hist.name + ".*"))
        for x in old[:-5]:
            x.unlink()
    shutil.copy2(str(src), str(dst))


class Interrupted(BaseException):
    """SIGTERM/SIGHUP during localize: treated like Ctrl-C (roll back, then stop)."""


def has_remote(p):
    return bool(gout(p, "remote"))


def exclude_file(p):
    r = gout(p, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")
    if not r:
        raise DocsmigError("cannot locate info/exclude", EXIT_MANUAL)
    return Path(r)


def is_localized_repo(p):
    try:
        return EXCLUDE_MARK in exclude_file(p).read_bytes()
    except (OSError, DocsmigError):
        return False


def ignore_line(rel):
    """Anchored, escaped ignore line that matches exactly one path."""
    s = re.sub(r"([\\*?\[\]!#])", r"\\\1", rel)
    if s.endswith(" "):
        s = s[:-1] + "\\ "
    return ("/" + s).encode("utf-8", "surrogateescape")


def append_bytes(f, lines):
    cur = f.read_bytes() if f.exists() else b""
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "ab") as fh:
        fh.write((b"\n" if cur and not cur.endswith(b"\n") else b"") + b"\n".join(lines) + b"\n")


def ensure_excludes(p, rels):
    """Local-only ignore rules in .git/info/exclude (bytes-safe, never committed). Returns the lines added."""
    f = exclude_file(p)
    have = {l.strip() for l in (f.read_bytes() if f.exists() else b"").splitlines()}
    add = [l for l in EXCLUDE_LINES if l not in have]
    if add:
        append_bytes(f, ([EXCLUDE_MARK] if EXCLUDE_MARK not in have else []) + add)
    extra = [l for l in (ignore_line(r) for r in rels if not is_ignored(p, r)) if l not in have]
    if extra:
        append_bytes(f, extra)
    return [l.decode("utf-8", "replace") for l in add + extra]


def lit_list(p, *args):
    return [x for x in git(p, *args, env_extra=LITERAL, check=False).stdout.split("\0") if x]


def index_entries(p, paths):
    """Exact index entries `mode sha stage<TAB>path` for paths."""
    res = []
    for i in range(0, len(paths), 200):
        res += lit_list(p, "ls-files", "-s", "-z", "--", *paths[i:i + 200])
    return res


def flagged_entries(p, paths):
    """Entries marked assume-unchanged (lowercase tag) or skip-worktree (S): git would hide changes to them."""
    res = []
    for i in range(0, len(paths), 200):
        for e in lit_list(p, "ls-files", "-v", "-z", "--", *paths[i:i + 200]):
            if e[:1].islower() or e[:1] == "S":
                res.append(e[2:])
    return res


def in_nested_repo(p, rel):
    """rel lies inside a submodule or a nested repo of p (gitlink in the index, or a folder with its own .git)."""
    parts = Path(rel).parts[:-1]
    for i in range(1, len(parts) + 1):
        d = p.joinpath(*parts[:i])
        if (d / ".git").exists():
            return True
        ent = lit_list(p, "ls-files", "-s", "-z", "--", "/".join(parts[:i])) if (p / ".git").exists() else []
        if ent and ent[0].startswith("160000"):
            return True
    return False


def refs_tracking(p, paths, skip):
    """(ref, paths) for every branch, tag, remote branch or stash entry outside `skip` that tracks any of paths:
    switching to it would overwrite the ignored local file, and switching back would delete it."""
    hits = []
    if not paths:
        return hits
    refs = [l.split(" ", 1) for l in gout(p, "for-each-ref", "--format=%(objectname) %(refname)",
                                            "refs/heads", "refs/tags", "refs/remotes").splitlines() if " " in l]
    refs += [[h, "stash@%s" % h] for h in gout(p, "log", "-g", "--format=%H", "refs/stash").splitlines()]
    by_commit = {}
    for sha, ref in refs:
        if ref not in skip and not ref.endswith("/HEAD"):
            by_commit.setdefault(sha, []).append(ref)
    if not by_commit:
        return hits
    query = "".join("%s:%s\n" % (sha, path) for sha in by_commit for path in paths)
    r = subprocess.run(["git", "-C", str(p), "cat-file", "--batch-check=%(objecttype)"], input=query, env=clean_env(),
                       capture_output=True, text=True, timeout=300)
    answers = r.stdout.splitlines()
    i = 0
    for sha in by_commit:
        found = []
        for path in paths:
            if i < len(answers) and not answers[i].endswith("missing"):
                found.append(path)
            i += 1
        if found:
            hits.append((by_commit[sha][0], found[:3]))
    return hits


def upstream_doc_changes(p, gf, branch, paths):
    """Commits on the default branch / the upstream that this checkout lacks and that touch legacy docs: their
    edits are not in the snapshot, so the new docs would miss them."""
    res = []
    up = gout(p, "rev-parse", "--abbrev-ref", branch + "@{upstream}")
    for ref in sorted({gf.get("default_ref") or "", up} - {""}):
        if paths and git(p, "rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0:
            n = gout(p, "rev-list", "--count", "HEAD..%s" % ref, "--", *paths)
            if n.isdigit() and int(n):
                res.append("%s: %s commit(s)" % (ref, n))
    return res


def disk_bytes(rel_disk, data):
    """The index moves into .claude/: its `@AGENTS.md` import must still point at the root file."""
    if rel_disk == INDEX_LOCAL:
        return re.sub(rb"(?m)^@AGENTS\.md[ \t]*$", b"@../AGENTS.md", data)
    return data


def atomic_write(dst, data, root, tmpdir):
    """Write via a temp file outside the work tree, then rename into place (never through a symlink)."""
    if dst.is_symlink() or path_has_symlink(root, dst.relative_to(root)):
        raise DocsmigError("refusing to write through symlink %s" % dst, EXIT_MANUAL)
    dst.parent.mkdir(parents=True, exist_ok=True)
    for tmp in (Path(tmpdir) / ("w-" + hashlib.sha1(str(dst).encode()).hexdigest()[:12]),
                dst.with_name(".%s.docsmig-tmp.local.md" % dst.name)):  # second: run dir on another volume
        fd = os.open(str(tmp), os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        try:
            os.replace(str(tmp), str(dst))
            return
        except OSError as e:
            tmp.unlink()
            if getattr(e, "errno", None) != 18:  # EXDEV: retry next to the target
                raise
    raise DocsmigError("could not write %s" % dst)


class Journal:
    """Written before every step, so a run that dies anywhere can still be undone exactly."""

    def __init__(self, path, data):
        self.path, self.data = path, data
        self.data.setdefault("steps", [])
        self.save()

    def step(self, **kw):
        self.data["steps"].append(kw)
        self.save()

    def save(self):
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(self.path))


def localize_undo(p, j):
    """Undo exactly the journaled steps, newest first. Anything changed since by someone else is never overwritten;
    an edited doc that would lose its ignore rule is moved out of the tree into the backup's rejected/."""
    notes = []
    rej = Path(j["backup"]) / "rejected"
    for st in reversed(j["steps"]):
        kind, rel = st["kind"], st.get("path", "")
        f = p / rel if rel else None
        try:
            if kind == "exclude" and st.get("keep"):
                notes.append("ignore rules kept (other worktrees share them)")
            elif kind == "exclude":
                ex = Path(st["file"])
                cur = ex.read_bytes() if ex.exists() else None
                if cur is not None and st.get("after") and hashlib.sha256(cur).hexdigest() != st["after"]:
                    notes.append("exclude file changed since — left as is")
                elif st["before"] is None:
                    if ex.exists():
                        ex.unlink()
                else:
                    ex.write_bytes(Path(st["before"]).read_bytes())
            elif kind == "link":
                if f.is_symlink() and os.readlink(str(f)) == st["target"]:
                    f.unlink()
                if st.get("backup") and not f.exists() and not f.is_symlink():
                    safe_copy(Path(st["backup"]), f, root=p)
            elif kind == "write":
                if f.is_file() and not f.is_symlink() and sha256(f) == st["sha256"]:
                    f.unlink()
                elif f.is_file() and not f.is_symlink():
                    notes.append("edited %s moved to %s" % (rel, stash_to(rej, rel, f)))
                elif f.is_symlink():
                    notes.append("kept %s (replaced by a link since)" % rel)
            elif kind == "delete":
                if not f.exists() and not f.is_symlink():
                    safe_copy(Path(st["backup"]), f, root=p)
                elif not (f.is_file() and sha256(f) == st["sha256"]):
                    notes.append("kept %s (exists again)" % rel)
            elif kind == "index":
                now_in = {e.split("\t", 1)[1] for e in index_entries(p, [e.split("\t", 1)[1] for e in st["entries"]])}
                missing = [e for e in st["entries"] if e.split("\t", 1)[1] not in now_in]
                if missing:
                    r = subprocess.run(["git", "-C", str(p), "-c", "core.hooksPath=/dev/null", "update-index", "-z",
                                        "--index-info"], input="".join(e + "\0" for e in missing), env=clean_env(),
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode != 0:
                        notes.append("index entries not restored: %s" % r.stderr.strip()[:120])
            elif kind == "ref":
                if gout(p, "rev-parse", "--verify", "--quiet", "refs/heads/" + st["branch"]) == st["new"]:
                    git(p, "update-ref", "-m", "docsmig localize undo", "refs/heads/" + st["branch"], st["old"], st["new"])
                elif st["old"] != st["new"] and gout(p, "rev-parse", "--verify", "--quiet",
                                                     "refs/heads/" + st["branch"]) != st["old"]:
                    notes.append("branch %s moved since — left where it is" % st["branch"])
            elif kind == "branch":  # the docs side branch dropped during the run
                if git(p, "show-ref", "--verify", "--quiet", "refs/heads/" + st["name"], check=False).returncode != 0:
                    git(p, "update-ref", "refs/heads/" + st["name"], st["sha"], "", check=False)
        except (OSError, DocsmigError, subprocess.SubprocessError) as e:
            notes.append("%s %s: %s" % (kind, rel, e))
    return notes


def pending_journals(pr):
    """Journals of runs that never finished nor rolled back (hard kill): they still need their undo."""
    res = []
    for jf in sorted(pr.glob("pre-localize-*/journal.json")):
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not d.get("done") and not d.get("rolled_back"):
            res.append((jf, d))
    return res


def recover_pending(p, pr):
    notes = []
    for jf, d in pending_journals(pr):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        try:
            n = localize_undo(p, d)
        finally:
            signal.signal(signal.SIGINT, signal.default_int_handler)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGHUP, signal.SIG_DFL)
        d["rolled_back"] = {"error": "interrupted run recovered", "notes": n, "time": now()}
        jf.write_text(json.dumps(d, indent=1), encoding="utf-8")
        notes.append("undid an interrupted run (%s)%s" % (jf.parent.name, "; " + "; ".join(n) if n else ""))
    return notes


def localize_problems(p, branch, tip, gone, disk_docs, link, links):
    probs = []
    if gout(p, "branch", "--show-current") != branch or gout(p, "rev-parse", "HEAD") != tip:
        probs.append("checkout is not %s@%s" % (branch, tip[:10]))
    names = sorted(set(gone) | set(disk_docs) | {"CLAUDE.md", "AGENTS.md"})
    still = lit_list(p, "ls-files", "-z", "--", *names)
    if still:
        probs.append("still tracked: %s" % still[:5])
    st = lit_list(p, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames", "--", *names)
    if st:
        probs.append("git status still shows docs: %s" % st[:5])
    for r in disk_docs:
        f = p / r
        if r in links:
            if not (f.is_symlink() and os.readlink(str(f)) == links[r]):
                probs.append("link missing: %s" % r)
        elif not f.is_file() or f.is_symlink():
            probs.append("missing %s" % r)
        if not is_ignored(p, r):
            probs.append("not ignored: %s" % r)
        if (f.is_file() or f.is_symlink()) and \
                Path(gout(f.parent, "rev-parse", "--show-toplevel") or "/").resolve() != p.resolve():
            probs.append("%s sits in another repo" % r)
    if link and not ((p / "AGENTS.md").is_symlink() and os.readlink(str(p / "AGENTS.md")) == AGENTS_LOCAL
                     and is_ignored(p, "AGENTS.md")):
        probs.append("AGENTS.md link missing or not ignored")
    probs += ["legacy file still on disk: %s" % r for r in gone if r not in ("CLAUDE.md", "AGENTS.md") and (p / r).exists()]
    if (p / "CLAUDE.md").exists():
        probs.append("root CLAUDE.md still on disk (the index is %s)" % INDEX_LOCAL)
    return probs


def write_mirror(slug, p, files, links=None):
    """Copy the local docs outside the work tree (git clean -X or an incoming commit could remove them); linked
    worktrees record their links instead, so audit --fix can re-create them."""
    m = mirror_dir(p)
    for r in files:
        f = p / r
        if f.is_file() and not f.is_symlink():
            mirror_put(m, r, f)
    if links:
        m.mkdir(parents=True, exist_ok=True)
        (m / ".links.json").write_text(json.dumps(links, indent=1), encoding="utf-8")
    try:
        os.chmod(str(MIRROR_ROOT), 0o700)
    except OSError:
        pass
    return m


def take_localize_lock(run_dir, key, slug, what):
    """Non-reentrant lock per repo for localize/unlocalize; a lock left by a dead process is taken over."""
    lk = LOCK_ROOT / (hashlib.sha1((key + "#localize").encode()).hexdigest()[:16] + ".lock")
    lk.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, ("%s %s %s pid %d\n" % (slug, what, now(), os.getpid())).encode())
            os.close(fd)
            return lk
        except FileExistsError:
            holder = lk.read_text(encoding="utf-8", errors="replace").strip()
            m = re.search(r"pid (\d+)", holder)
            alive = True
            if m:
                try:
                    os.kill(int(m.group(1)), 0)
                except ProcessLookupError:
                    alive = False
                except PermissionError:
                    pass
            if alive:
                raise DocsmigError("another localize holds the lock (%s) — if no docsmig is running, delete %s"
                                   % (holder, lk), EXIT_MANUAL)
            lk.unlink()  # its process is gone (hard kill): the journal tells what to undo
    raise DocsmigError("could not take the lock %s" % lk, EXIT_MANUAL)


def cmd_localize(args, run_dir):
    slug, p = resolve(args.slug)
    gf = git_facts(p)
    if gf is None:
        raise DocsmigError("%s is not the top of a git repo" % slug, EXIT_MANUAL)
    lk = take_localize_lock(run_dir, gf["common_dir"], slug, "localize")
    try:
        return _localize(args, run_dir)
    finally:
        try:
            lk.unlink()
        except OSError:
            pass


def _localize(args, run_dir):
    """Project docs stay on this machine. One commit untracks the legacy docs (nothing else). The index is written to
    .claude/CLAUDE.md and AGENTS.md becomes a link to AGENTS.local.md — paths no ref tracks, so branch switches and
    pulls cannot overwrite or delete them. The other docs keep their slot paths, ignored via .git/info/exclude.
    --link-from DIR links every doc to a shared folder instead (several worktrees of one repo).
    Unpushed docs commits from an earlier adopt are replaced. Every step is journaled; failures roll back."""
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    pr = Path(plan["snapshot"]).parent
    if plan["mode"] != "git":
        raise DocsmigError("%s is mode %s — not a git checkout, the docs are already local" % (slug, plan["mode"]))
    if (pr / "localized.json").exists():
        raise DocsmigError("%s already localized" % slug)
    if getattr(args, "check", False) and pending_journals(pr):
        print("MANUAL: an interrupted localize needs undoing first — run localize (it undoes it) or restore")
        return EXIT_MANUAL
    for n in recover_pending(p, pr):  # first: a hard-killed earlier run must be undone before anything is read
        print("note: " + n)
    gf = git_facts(p)
    if gf is None:
        raise DocsmigError("%s is not the top of a git repo" % slug, EXIT_MANUAL)
    link_from = getattr(args, "link_from", None)
    rec = json.loads((pr / "commit.json").read_text(encoding="utf-8")) if (pr / "commit.json").exists() else None
    ad = json.loads((pr / "adopt.json").read_text(encoding="utf-8")) if (pr / "adopt.json").exists() else None
    if link_from and (rec or ad):
        raise DocsmigError("--link-from is for freshly prepared checkouts only", EXIT_MANUAL)
    if rec is None and not link_from:
        rc = report_verify(verify(plan), plan)
        if rc != EXIT_OK:
            return rc
    manifest = load_manifest(plan)
    keep = parse_keep(plan)
    out = Path(plan["out"])
    legacy = sorted(r for r, m in manifest.items() if m["class"] == "legacy" and r not in keep)
    links = {}
    if link_from:
        canon = Path(link_from).expanduser().resolve()
        if not (canon / INDEX_LOCAL).is_file() or not (canon / INDEX_LOCAL).read_bytes():
            raise DocsmigError("%s has no %s" % (canon, INDEX_LOCAL), EXIT_MANUAL)
        try:
            canon.relative_to(p.resolve())
            raise DocsmigError("the shared docs folder must live outside the checkout", EXIT_MANUAL)
        except ValueError:
            pass
        other = inside_other_worktree(canon)
        if other:
            raise DocsmigError("%s sits inside the git work tree %s" % (canon, other), EXIT_MANUAL)
        lost = legacy_not_in_shared(p, load_manifest(plan), sorted(r for r, m in load_manifest(plan).items()
                                                                    if m["class"] == "legacy"), canon, run_dir)
        if (lost is None or lost) and not getattr(args, "ack_legacy_loss", False):
            (pr / "legacy-not-in-shared.txt").write_text("\n".join(lost or ["(source of the shared folder unknown)"])
                                                         + "\n", encoding="utf-8")
            print("MANUAL: %s of this worktree's legacy lines are not in the shared docs (first: %s) — list in %s; "
                  "port them, or pass --ack-legacy-loss (they stay in this branch's git history)"
                  % ("?" if lost is None else len(lost), (lost or ["unknown source"])[0],
                     pr / "legacy-not-in-shared.txt"))
            return EXIT_MANUAL
        for f in sorted(canon.rglob("*")):
            if f.is_file() and not f.is_symlink():
                r = str(f.relative_to(canon))
                links[r] = os.path.relpath(str(f), str((p / r).parent))
        for n in plan["allowed_slots"]:  # unwritten slots: links that point where the file will be created
            r = "docs/%02d-%s.md" % (n, SLOTS[n])
            links.setdefault(r, os.path.relpath(str(canon / r), str((p / r).parent)))
        docs = []
    else:
        docs = out_files(out)
    disk = {r: DISK_NAME.get(r, r) for r in docs}
    # ---- preconditions (nothing is changed until all pass)
    if gf["in_progress"]:
        print("MANUAL: git operation in progress (%s)" % gf["in_progress"])
        return EXIT_MANUAL
    branch, old_tip = gf["branch"], gf["head"]
    if not branch or not old_tip:
        print("MANUAL: detached HEAD or no commits yet")
        return EXIT_MANUAL
    if (gf["worktrees"] > 1 or gf["linked_worktree"]) and not link_from:
        print("MANUAL: the repo has %d worktrees — give them one shared docs folder (materialize + --link-from)"
              % gf["worktrees"])
        return EXIT_MANUAL
    if git(p, "diff", "--cached", "--quiet", check=False).returncode != 0:
        print("MANUAL: staged changes in the index — commit or unstage them first")
        return EXIT_MANUAL
    if any(e[:2] == " A" for e in gz(p, "status", "--porcelain=v1", "-z", "--untracked-files=no")):
        print("MANUAL: intent-to-add entries in the index — commit or drop them first")
        return EXIT_MANUAL
    skip = {"refs/heads/" + branch}
    if rec and gout(p, "rev-parse", "--verify", "--quiet", "refs/heads/" + BRANCH) == rec.get("commit_b"):
        skip.add("refs/heads/" + BRANCH)  # dropped in the act phase
    if ad:
        if ad["strategy"] != "ff":
            print("MANUAL: adopted through a PR — the docs are already on the remote")
            return EXIT_MANUAL
        if branch != ad["branch"] or old_tip != ad["adopted_tip"]:
            print("MANUAL: checkout is %s@%s but the adopted tip was %s@%s — commits were added since"
                  % (branch, old_tip[:10], ad["branch"], ad["adopted_tip"][:10]))
            return EXIT_MANUAL
        if gout(p, "branch", "-r", "--contains", old_tip):
            print("MANUAL: the adopted docs commits are already on a remote branch")
            return EXIT_MANUAL
        carriers = [r for r in gout(p, "for-each-ref", "--format=%(refname)", "--contains", rec["commit_b"]).splitlines()
                    if r not in skip]
        if carriers:
            print("MANUAL: other refs contain the adopted docs commit: %s — a switch there would delete the local docs"
                  % carriers[:4])
            return EXIT_MANUAL
        parent = ad["pre_adopt"]
        odd = [c for c in gz(p, "diff", "-z", "--no-renames", "--name-only", parent, old_tip, "--")
               if c not in legacy and c not in docs]
        if odd:
            print("MANUAL: the adopted commits touch non-doc paths %s" % odd[:5])
            return EXIT_MANUAL
        missing = [r for r in docs if not (p / r).is_file() and not (p / disk[r]).is_file()]
        if missing:
            print("MANUAL: adopted doc files missing on disk: %s" % missing[:5])
            return EXIT_MANUAL
        back = [r for r in legacy if r not in docs and (p / r).exists()]
        if back:
            print("MANUAL: legacy file(s) on disk next to the adopted docs: %s — merge their edits by hand" % back[:5])
            return EXIT_MANUAL
    else:
        parent = old_tip
        for r in legacy:
            f = p / r
            if f.is_symlink() or path_has_symlink(p, r):
                print("MANUAL: symlink at %s" % r)
                return EXIT_MANUAL
            if f.exists() and sha256(f) != manifest[r]["sha256"]:
                print("drift: %s changed since prepare — re-run prepare" % r)
                return EXIT_DRIFT
        for r in docs:
            if r in manifest and (p / r).exists() and sha256(p / r) != manifest[r]["sha256"]:
                print("drift: %s changed since prepare — re-run prepare" % r)
                return EXIT_DRIFT
            if disk[r] != r and (p / r).exists() and r not in manifest:
                print("MANUAL: %s appeared since prepare — move it aside first" % r)
                return EXIT_MANUAL
        if rec:
            for c in filter(None, (rec.get("commit_b"), rec.get("commit_a"))):
                if gout(p, "branch", "-r", "--contains", c):
                    print("MANUAL: the docs commit %s is on a remote branch — the docs already left this machine" % c[:10])
                    return EXIT_MANUAL
            for r in rec["commit_outputs"]:
                want = gout(p, "rev-parse", "--verify", "--quiet", "%s:%s" % (rec["commit_b"], r))
                if not want or r not in docs or gout(p, "hash-object", "--path=" + r, str(out / r)) != want:
                    print("MANUAL: out/%s differs from the verified docs commit" % r)
                    return EXIT_MANUAL
            claude_b = gout(p, "rev-parse", "--verify", "--quiet", "%s:CLAUDE.md" % rec["commit_b"])
            for ref in gout(p, "for-each-ref", "--format=%(refname)", "refs/remotes").splitlines():
                if claude_b and gout(p, "rev-parse", "--verify", "--quiet", "%s:CLAUDE.md" % ref) == claude_b:
                    print("MANUAL: %s already carries the new CLAUDE.md (merged docs PR?)" % ref)
                    return EXIT_MANUAL
    agents_tracked = tracked_at(p, parent, "AGENTS.md")
    if (p / "AGENTS.md").is_symlink():
        print("MANUAL: AGENTS.md is a symlink — handle it by hand")
        return EXIT_MANUAL
    gone = [r for r in legacy if tracked_at(p, parent, r)]
    if agents_tracked and "AGENTS.md" not in gone:
        gone.append("AGENTS.md")
    late = upstream_doc_changes(p, gf, branch, gone)
    if late and not getattr(args, "ack_upstream_docs", False):
        print("MANUAL: %s change the old docs and are not in this checkout — merge/rebase first, or pass "
              "--ack-upstream-docs and port those edits into the new docs afterwards" % "; ".join(late))
        return EXIT_MANUAL
    # the bytes each disk path must end up with (adopted: what is on disk now, edits after adopt included)
    content, source = {}, {}
    if not link_from:
        for r in docs:
            src = p / r if ad and (p / r).is_file() else (p / disk[r] if ad else out / r)
            source[r] = src.read_bytes()
            content[disk[r]] = disk_bytes(disk[r], source[r])
        if agents_tracked and AGENTS_LOCAL not in content:
            if not (p / "AGENTS.md").is_file():
                print("MANUAL: AGENTS.md is tracked but missing on disk")
                return EXIT_MANUAL
            content[AGENTS_LOCAL] = (p / "AGENTS.md").read_bytes()
    elif agents_tracked:
        if AGENTS_LOCAL not in links:
            print("MANUAL: AGENTS.md is tracked but the shared folder has no %s" % AGENTS_LOCAL)
            return EXIT_MANUAL
    link = agents_tracked
    disk_docs = sorted(links) if link_from else sorted(content)
    for r in disk_docs + ["AGENTS.md"]:
        if in_nested_repo(p, r):
            print("MANUAL: %s would sit inside a submodule or nested repo" % r)
            return EXIT_MANUAL
        if str(Path(r).parent) != "." and path_has_symlink(p, str(Path(r).parent)):
            print("MANUAL: symlink on the path of %s" % r)
            return EXIT_MANUAL
    tracked_here = lit_list(p, "ls-tree", "-r", "-z", "--name-only", parent, "--", *disk_docs)
    if tracked_here:
        print("MANUAL: %s already tracked in git — a doc can't live there locally" % tracked_here[:4])
        return EXIT_MANUAL
    carriers = refs_tracking(p, disk_docs, skip)
    if carriers:
        print("MANUAL: %s track doc path(s) %s — switching there would overwrite the local docs; delete or rebase "
              "those refs first" % ([c[0] for c in carriers[:4]], carriers[0][1]))
        return EXIT_MANUAL
    for r in disk_docs:
        f = p / r
        if link_from:
            if f.is_symlink() and os.readlink(str(f)) == links[r]:
                continue
            if f.exists() or f.is_symlink():
                print("MANUAL: %s already exists — move it aside first" % r)
                return EXIT_MANUAL
            continue
        if f.is_symlink():
            print("MANUAL: %s is a symlink" % r)
            return EXIT_MANUAL
        if f.exists() and f.read_bytes() != content[r]:
            print("MANUAL: %s already exists and differs — move it aside first" % r)
            return EXIT_MANUAL
    flagged = flagged_entries(p, sorted(set(gone) | set(docs)))
    if flagged:
        print("MANUAL: assume-unchanged/skip-worktree flags on %s — clear them first" % flagged[:5])
        return EXIT_MANUAL
    # CI workflows deploy a fresh checkout of tracked files, so local-only docs never reach them; a script reviewed
    # by hand (it uploads a subfolder that only looks like the root) is passed with --deploy-reviewed
    reviewed = set(getattr(args, "deploy_reviewed", None) or [])
    blk = [b for b in deploy_blockers(p, True, {Path(r).name for r in plan["legacy"]}, need_claude_dir=True)
           if not re.match(r"\.github/workflows/[^/]+\.ya?ml$", b[0]) and b[0] not in reviewed]
    if blk:
        print("MANUAL: deploy blocker(s) %s — exclude /docs/, /.claude/ and *.local.md from the upload first"
              % [b[0] for b in blk])
        return EXIT_MANUAL
    # ---- the untrack commit (objects only — nothing visible yet)
    tmpdir = tempfile.mkdtemp(prefix="docsmig-")
    ix = {"GIT_INDEX_FILE": os.path.join(tmpdir, "index")}
    try:
        git(p, "read-tree", parent, env_extra=ix)
        for r in gone:
            git(p, "update-index", "--force-remove", "--", r, env_extra=ix)
        tree = gout(p, "write-tree", env_extra=ix)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not tree:
        raise DocsmigError("write-tree failed")
    if AI_WORDS.search(LOCALIZE_MSG):
        raise DocsmigError("commit message contains AI attribution")
    new_tip = parent
    if tree != gout(p, "rev-parse", parent + "^{tree}"):
        new_tip = gout(p, "commit-tree", tree, "-p", parent, "-m", LOCALIZE_MSG)
        if not new_tip:
            raise DocsmigError("commit-tree failed")
    plan_text = "%s: %s%s; untrack %d legacy file(s) %s; %d doc file(s) %s, ignored (index %s%s)%s" % (
        branch, "rewind the unpushed docs commits to %s, then " % parent[:10] if ad else "",
        "one commit" if new_tip != parent else "no commit needed", len(gone), gone[:6], len(disk_docs),
        "linked to %s" % link_from if link_from else "on disk", INDEX_LOCAL,
        ", AGENTS.md -> %s" % AGENTS_LOCAL if link else "", "; upstream doc edits to port: %s" % late if late else "")
    if getattr(args, "check", False):
        print("would localize %s on %s" % (slug, plan_text))
        return EXIT_OK
    # ---- act: one run at a time per repo; every step journaled before it happens; any failure or signal rolls back
    backup = pr / ("pre-localize-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))
    old_handlers = {}
    j = None
    try:
        backup.mkdir(parents=True)
        (backup / "tmp").mkdir()
        excl = exclude_file(p)
        if excl.exists():
            shutil.copy2(str(excl), str(backup / "exclude.before"))
        j = Journal(backup / "journal.json", {"slug": slug, "branch": branch, "old_tip": old_tip, "new_tip": new_tip,
                                              "parent": parent, "untracked": gone, "local_docs": disk_docs,
                                              "links": links, "backup": str(backup), "time": now()})

        def _raise(signum, frame):
            raise Interrupted("signal %d" % signum)
        for sig in (signal.SIGTERM, signal.SIGHUP):
            old_handlers[sig] = signal.signal(sig, _raise)
        added = []
        if new_tip != old_tip:
            j.step(kind="ref", branch=branch, old=old_tip, new=new_tip)
            git(p, "update-ref", "-m", "docsmig localize", "refs/heads/" + branch, new_tip, old_tip)  # compare-and-swap
        if "refs/heads/" + BRANCH in skip:
            j.step(kind="branch", name=BRANCH, sha=rec["commit_b"])
            git(p, "branch", "--unset-upstream", BRANCH, check=False)
            git(p, "update-ref", "-d", "refs/heads/" + BRANCH, rec["commit_b"])
        index_paths = sorted(set(gone) | set(docs) | set(disk_docs))
        entries = index_entries(p, index_paths)
        if entries:
            j.step(kind="index", entries=entries)
            for i in range(0, len(index_paths), 200):  # index: drop exactly these entries, files stay on disk
                git(p, "rm", "--cached", "-f", "-q", "--ignore-unmatch", "--", *index_paths[i:i + 200], env_extra=LITERAL)
        for r in disk_docs:
            f = p / r
            if link_from:
                if f.is_symlink() and os.readlink(str(f)) == links[r]:
                    continue
                if f.exists() or f.is_symlink():
                    raise DocsmigError("%s appeared during the run" % r, EXIT_MANUAL)
                j.step(kind="link", path=r, target=links[r], backup="")
                f.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(links[r], str(f))
                continue
            if f.is_file() and not f.is_symlink() and f.read_bytes() == content[r]:
                continue
            if f.exists() or f.is_symlink():
                raise DocsmigError("%s changed during the run" % r, EXIT_MANUAL)
            j.step(kind="write", path=r, sha256=hashlib.sha256(content[r]).hexdigest())
            atomic_write(f, content[r], p, backup / "tmp")
        moved = [r for r in docs if disk[r] != r and (p / r).is_file() and not (p / r).is_symlink()]
        for r in moved + [r for r in legacy if r not in docs and r not in moved]:
            f = p / r
            if not f.is_file() or f.is_symlink():
                continue
            if r == "AGENTS.md" and link:
                continue
            if r in moved and (f.read_bytes() != source[r] if ad else sha256(f) != manifest[r]["sha256"]):
                raise DocsmigError("%s changed during the run" % r, EXIT_MANUAL)
            if r not in moved and sha256(f) != manifest[r]["sha256"]:
                continue  # an edited legacy file stays; the end-state check reports it
            (backup / "files" / r).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(f), str(backup / "files" / r))
            j.step(kind="delete", path=r, backup=str(backup / "files" / r), sha256=sha256(f))
            f.unlink()
            d = f.parent
            while d != p and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
        if link:
            a = p / "AGENTS.md"
            bk = ""
            if a.is_file() and not a.is_symlink():
                (backup / "files").mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(a), str(backup / "files" / "AGENTS.md"))
                bk = str(backup / "files" / "AGENTS.md")
            j.step(kind="link", path="AGENTS.md", target=AGENTS_LOCAL, backup=bk)
            if a.exists() or a.is_symlink():
                a.unlink()
            os.symlink(AGENTS_LOCAL, str(a))
        before = excl.read_bytes() if excl.exists() else None
        j.step(kind="exclude", file=str(excl), before=str(backup / "exclude.before") if before is not None else None,
               after=None, keep=bool(link_from))
        added = ensure_excludes(p, disk_docs + (["AGENTS.md"] if link else []))
        j.data["steps"][-1]["after"] = hashlib.sha256(excl.read_bytes()).hexdigest()
        j.save()
        probs = localize_problems(p, branch, new_tip, gone, disk_docs, link, links)
        if probs:
            raise DocsmigError("; ".join(probs), EXIT_MANUAL)
        if ad:  # the reflog still points at the dropped docs commits: `checkout HEAD@{1}` would clobber the docs
            drop = {old_tip, rec.get("commit_b"), rec.get("commit_a")} - {None, ""}
            for ref in ("HEAD", "refs/heads/" + branch):
                for ent in reversed(gout(p, "reflog", "show", "--format=%gd %H", ref).splitlines()):
                    sel, _, sha = ent.partition(" ")
                    if sha in drop:
                        git(p, "reflog", "delete", sel, check=False)
        mirror = str(write_mirror(slug, p, disk_docs, links if link_from else None))
        j.data.update({"exclude_added": added, "deploy_reviewed": sorted(reviewed), "mirror": mirror,
                       "upstream_docs_to_port": late, "done": now()})
        (pr / "localized.json").write_text(json.dumps(j.data, indent=1), encoding="utf-8")
        j.save()
    except BaseException as e:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)  # a second Ctrl-C must not cut the rollback short
        notes = localize_undo(p, j.data) if j else []
        if j:
            j.data["rolled_back"] = {"error": "%s: %s" % (type(e).__name__, e), "notes": notes, "time": now()}
            j.save()
        print("MANUAL: localize failed and was rolled back (%s: %s)%s%s" % (
            type(e).__name__, e, "; " + "; ".join(notes) if notes else "", " — journal %s" % j.path if j else ""))
        return EXIT_MANUAL
    finally:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        for sig, h in old_handlers.items():
            signal.signal(sig, h)
    release_lock(plan)
    up = gout(p, "rev-parse", "--abbrev-ref", branch + "@{upstream}")
    print("localized %s on %s; nothing pushed" % (slug, plan_text))
    if new_tip != parent and up:
        print("  note: %s is 1 commit ahead of %s until your next PR; if `git pull` reports diverged branches,"
              " use `git pull --rebase`" % (branch, up))
    if late:
        print("  todo: port the upstream doc edits (%s) into the new docs" % "; ".join(late))
    return EXIT_OK


def cmd_unlocalize(p, pr, slug, run_dir):
    """restore --after-localize: undo a finished localize from its journal, if nothing was committed on top.
    Safe to re-run after an interruption: every undo step is guarded."""
    j = json.loads((pr / "localized.json").read_text(encoding="utf-8"))
    head = gout(p, "rev-parse", "HEAD")
    if gout(p, "branch", "--show-current") != j["branch"] or head not in (j["new_tip"], j["old_tip"]):
        raise DocsmigError("checkout is not %s@%s (commits were added since) — undo by hand from %s"
                           % (j["branch"], j["new_tip"][:10], j["backup"]), EXIT_MANUAL)
    gf = git_facts(p)
    lk = take_localize_lock(run_dir, (gf or {}).get("common_dir", str(p)), slug, "unlocalize")
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_IGN)
    try:
        notes = localize_undo(p, j)
        os.rename(str(pr / "localized.json"), str(pr / ("localized.json.undone-" + datetime.datetime.now()
                                                           .strftime("%Y%m%d%H%M%S"))))
    finally:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_DFL)
        try:
            lk.unlink()
        except OSError:
            pass
    for n in notes:
        print(n)
    print("unlocalized %s: back on %s@%s" % (slug, j["branch"], j["old_tip"][:10]))
    return EXIT_OK


def inside_other_worktree(folder):
    """A shared docs folder must not sit in any git work tree (there `git add -A` would commit the docs)."""
    d = Path(folder)
    while not d.exists() and d != d.parent:
        d = d.parent
    top = gout(d, "rev-parse", "--show-toplevel")
    return top if top and not is_ignored(Path(top), os.path.relpath(str(folder), top)) else ""


def legacy_not_in_shared(p, manifest, legacy, canon, run_dir):
    """Lines of this worktree's legacy docs that neither the shared folder nor the materialized source covers:
    content that only this branch has and that deleting its legacy files would drop."""
    src_snap = None
    for mj in run_dir.glob("*/materialized.json"):
        try:
            if Path(json.loads(mj.read_text(encoding="utf-8"))["dir"]) == canon:
                src_snap = mj.parent / "snapshot"
        except (OSError, ValueError, KeyError):
            pass
    have = set()
    for f in canon.rglob("*"):
        if f.is_file():
            have |= {norm(l) for l in read_lines(f)}
    if src_snap is None:
        return None  # unknown source: cannot prove nothing is lost
    for f in src_snap.rglob("*"):
        if f.is_file():
            have |= {norm(l) for l in read_lines(f)}  # the source migration handled these (moved or ledgered)
    lost = []
    for r in legacy:
        f = p / r
        if f.is_file() and not f.is_symlink():
            lost += ["%s: %s" % (r, norm(l)[:100]) for l in read_lines(f) if significant(norm(l)) and norm(l) not in have]
    return lost


def cmd_materialize(args, run_dir):
    """Write a prepared+verified project's out/ into a shared docs folder (disk names: .claude/CLAUDE.md,
    AGENTS.local.md) for worktrees that link to it with `localize --link-from`."""
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    dst = Path(args.dir).expanduser().resolve()
    try:
        dst.relative_to(p.resolve())
        raise DocsmigError("the shared folder must live outside the checkout", EXIT_MANUAL)
    except ValueError:
        pass
    if dst.exists() and any(dst.iterdir()):
        raise DocsmigError("%s exists and is not empty" % dst, EXIT_MANUAL)
    other = inside_other_worktree(dst)
    if other:
        raise DocsmigError("%s sits inside the git work tree %s — pick a folder outside every repo" % (dst, other),
                           EXIT_MANUAL)
    rc = report_verify(verify(plan), plan)
    if rc != EXIT_OK:
        return rc
    out = Path(plan["out"])
    agents_here = (p / "AGENTS.md").is_file() and not (p / "AGENTS.md").is_symlink()
    files = []
    for r in out_files(out):
        d = DISK_NAME.get(r, r)
        (dst / d).parent.mkdir(parents=True, exist_ok=True)
        (dst / d).write_bytes(disk_bytes(d, (out / r).read_bytes()))
        files.append(d)
    if agents_here and AGENTS_LOCAL not in files:
        shutil.copy2(str(p / "AGENTS.md"), str(dst / AGENTS_LOCAL))
        files.append(AGENTS_LOCAL)
    if AGENTS_LOCAL in files:  # the index imports @../AGENTS.md: resolve it inside the shared folder too
        os.symlink(AGENTS_LOCAL, str(dst / "AGENTS.md"))
    try:
        os.chmod(str(dst), 0o700)
    except OSError:
        pass
    pr_dir = Path(plan["snapshot"]).parent
    (pr_dir / "materialized.json").write_text(json.dumps({"dir": str(dst), "files": files, "time": now()}, indent=1),
                                               encoding="utf-8")
    print("materialized %s into %s: %d file(s); link each worktree with `localize <slug> --link-from %s`"
          % (slug, dst, len(files), dst))
    return EXIT_OK


def cmd_restore(args, run_dir):
    slug, p = resolve(args.slug)
    plan = load_plan(run_dir, slug, p)
    pr = Path(plan["snapshot"]).parent
    if (pr / "localized.json").exists():
        if not getattr(args, "after_localize", False):
            raise DocsmigError("%s was localized — use restore --after-localize" % slug, EXIT_MANUAL)
        return cmd_unlocalize(p, pr, slug, run_dir)
    if pending_journals(pr):
        gfr = git_facts(p) or {}
        lk = take_localize_lock(run_dir, gfr.get("common_dir", str(p)), slug, "recover")
        try:
            for n in recover_pending(p, pr):
                print(n)
        finally:
            try:
                lk.unlink()
            except OSError:
                pass
        print("restored %s: the interrupted localize was undone" % slug)
        return EXIT_OK
    if getattr(args, "after_localize", False):
        raise DocsmigError("%s has no localize to undo" % slug, EXIT_MANUAL)
    snap = Path(plan["snapshot"])
    manifest = load_manifest(plan)
    rej = pr / "rejected"
    actions = []
    if plan["mode"] == "git":
        adopted = (pr / "adopt.json").exists()
        if adopted and not args.after_adopt:
            raise DocsmigError("%s was adopted — use restore --after-adopt" % slug, EXIT_MANUAL)
        if args.after_adopt:
            ad = json.loads((pr / "adopt.json").read_text(encoding="utf-8"))
            if ad["strategy"] != "ff":
                raise DocsmigError("adopted through a PR — revert with a revert PR, not locally", EXIT_MANUAL)
            if gout(p, "branch", "--show-current") != ad["branch"] or gout(p, "rev-parse", "HEAD") != ad["adopted_tip"]:
                raise DocsmigError("checkout is not %s@%s (the adopted tip) — refusing to reset" %
                                   (ad["branch"], ad["adopted_tip"][:10]), EXIT_MANUAL)
            git(p, "reset", "--keep", ad["pre_adopt"])  # refuses on conflicts before anything else is touched
            actions.append("reset --keep to %s" % ad["pre_adopt"][:10])
            for item in ad["local_placed"]:
                f = p / item["path"]
                if f.exists():
                    if sha256(f) == item["sha256"]:
                        f.unlink()
                    else:
                        actions.append("kept edited %s in %s" % (item["path"], stash_to(rej, item["path"], f)))
        else:
            # never adopted: the checkout was never touched — only drop the branch, leave every file alone
            if (pr / "commit.json").exists():
                rec = json.loads((pr / "commit.json").read_text(encoding="utf-8"))
                if git(p, "rev-parse", "--abbrev-ref", BRANCH + "@{upstream}", check=False).returncode == 0:
                    raise DocsmigError("branch has an upstream — revert via PR instead", EXIT_MANUAL)
                r = git(p, "update-ref", "-d", "refs/heads/" + BRANCH, rec["commit_b"], check=False)
                actions.append("deleted %s" % BRANCH if r.returncode == 0 else "left %s (tip moved — has extra commits)" % BRANCH)
            release_lock(plan)
            (pr / "restored.json").write_text(json.dumps({"time": now(), "actions": actions}, indent=1), encoding="utf-8")
            for a in actions:
                print(a)
            print("restored %s (branch only; working tree untouched)" % slug)
            return EXIT_OK
    applied = pr / "applied.json"
    if applied.exists():
        for c in json.loads(applied.read_text(encoding="utf-8"))["copied"]:
            f = p / c["path"]
            if not f.exists() or c["path"] in manifest:
                continue
            if sha256(f) == c["sha256"]:
                f.unlink()
            else:
                actions.append("kept edited %s in %s" % (c["path"], stash_to(rej, c["path"], f)))
    for rel, m in manifest.items():
        if m["class"] != "legacy":
            continue
        dst = p / rel
        if dst.is_symlink():
            actions.append("skipped symlink %s" % rel)
            continue
        if dst.exists() and sha256(dst) == m["sha256"]:
            continue
        if dst.exists():
            actions.append("kept current %s in %s" % (rel, stash_to(rej, rel, dst)))
        safe_copy(snap / rel, dst, root=p)
    release_lock(plan)
    (pr / "restored.json").write_text(json.dumps({"time": now(), "actions": actions}, indent=1), encoding="utf-8")
    for a in actions:
        print(a)
    print("restored %s from snapshot%s" % (slug, " — edited files saved in %s" % rej if rej.exists() else ""))
    return EXIT_OK


def cmd_audit(args, run_dir):
    slug, p = resolve(args.slug)
    ptype, _ = detect_type(p)
    claude = index_file(p)
    text = claude.read_text(encoding="utf-8", errors="replace") if claude.exists() else ""
    dm = docs_map(text)
    issues = []
    gitrepo = git_facts(p) is not None
    localized = gitrepo and is_localized_repo(p)
    fix = getattr(args, "fix", False)
    mirror = mirror_dir(p)
    if localized and mirror.is_dir():  # restore local docs that git removed (clean -X, an incoming commit…)
        links = {}
        try:
            links = json.loads((mirror / ".links.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        for r, target in sorted(links.items()):
            cur = p / r
            if cur.is_symlink() and os.readlink(str(cur)) == target:
                continue
            if cur.exists() or cur.is_symlink():
                issues.append("%s should link to the shared docs but is now a file — edits there never reach the "
                              "shared folder; merge it by hand, then delete it and run audit --fix" % r)
            elif fix:
                cur.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(target, str(cur))
                print("  fixed: re-linked %s" % r)
            else:
                issues.append("link missing: %s — run audit --fix" % r)
        for f in sorted(mirror.rglob("*")):
            r = str(f.relative_to(mirror))
            if r.startswith(".history/") or r == ".links.json" or r in links:
                continue
            cur = p / r
            if f.is_file() and not cur.exists() and not cur.is_symlink():
                if lit_list(p, "ls-files", "-z", "--", r) or tracked_at(p, "HEAD", r):
                    issues.append("doc path %s is tracked in git now — resolve by hand (your copy: %s)" % (r, f))
                elif fix:
                    safe_copy(f, cur, root=p)
                    print("  fixed: restored %s from %s" % (r, mirror))
                else:
                    issues.append("local doc missing: %s (copy in %s) — run audit --fix" % (r, mirror))
        if fix:
            claude = index_file(p)
            text = claude.read_text(encoding="utf-8", errors="replace") if claude.exists() else ""
            dm = docs_map(text)
    if dm is None:
        if localized:
            print("%s: localized repo but no index with a Docs map — run audit --fix (mirror %s)" % (slug, mirror))
            for i in issues:
                print("  - " + i)
            return EXIT_FAIL
        print("%s: legacy (no Docs map) — type %s" % (slug, ptype))
        return EXIT_OK
    lines = text.splitlines()
    if len(lines) > 70:
        issues.append("%s %d lines (>70)" % (claude.name, len(lines)))
    docs = classify_docs(p)
    legacy_left = [r for r, c in docs.items() if c == "legacy" and r != "CLAUDE.md" and not (r.startswith("docs/") and
                   (Path(r).name in SLOT_FILES or Path(r).name in LOCAL_FILES) and len(Path(r).parts) == 2)]
    linked_text = text + "".join((p / "docs" / n).read_text(encoding="utf-8", errors="replace")
                                 for n in list(SLOT_FILES) + list(LOCAL_FILES) if (p / "docs" / n).is_file())
    legacy_left = [r for r in legacy_left if r not in linked_text and Path(r).name not in linked_text]  # linked = kept on purpose
    if legacy_left:
        issues.append("legacy files beside a Docs map: %s" % ", ".join(sorted(legacy_left)[:8]))
    for name, n in SLOT_FILES.items():
        f = p / "docs" / name
        lf = p / "docs" / ("%02d-%s.local.md" % (n, SLOTS[n]))
        row = dm.get(name)
        if (f.exists() or lf.exists()) and (row is None or row["unwritten"]):
            issues.append("map row missing/unwritten for existing %s" % name)
        if row and not row["unwritten"] and not (f.exists() or lf.exists()):
            issues.append("map lists %s but file is missing" % name)
        for x in (f, lf):
            if x.exists():
                body = x.read_text(encoding="utf-8", errors="replace")
                real = [l for l in body.splitlines() if significant(norm(l)) and not l.lstrip().startswith("#")]
                if not real or "<!-- GUIDE" in body:
                    issues.append("placeholder slot %s" % x.name)
                if len(body.splitlines()) > 300:
                    issues.append("%s over 300 lines" % x.name)
                if x == lf and gitrepo and not is_ignored(p, str(x.relative_to(p))):
                    issues.append("%s not ignored" % x.name)
                if x == f and any(has_secret(l) for l in body.splitlines()):
                    issues.append("secret pattern in %s" % x.name)
    if gitrepo and has_remote(p):  # project docs are local-only wherever a push could carry them
        mine = ["CLAUDE.md", INDEX_LOCAL, "CLAUDE.local.md", "AGENTS.md", AGENTS_LOCAL] + \
            ["docs/" + n for n in list(SLOT_FILES) + list(LOCAL_FILES)]
        tracked = lit_list(p, "ls-files", "-z", "--", *mine)
        tracked += [x for x in git(p, "ls-files", "-z", "--", "docs/ref/", ".claude/skills/", check=False).stdout.split("\0")
                    if x]
        tracked = sorted(set(tracked))
        if tracked:
            issues.append("docs tracked in git (must stay local): %s" % ", ".join(tracked[:6]))
        loose = [r for r in mine if (p / r).is_file() and r not in tracked and not is_ignored(p, r)]
        if loose:
            issues.append("docs not ignored (a commit could pick them up): %s" % ", ".join(loose[:6]))
        agents = p / "AGENTS.md"
        if localized and (p / AGENTS_LOCAL).is_file() and \
                not (agents.is_symlink() and os.readlink(str(agents)) == AGENTS_LOCAL):
            if fix and not agents.exists() and not agents.is_symlink():
                os.symlink(AGENTS_LOCAL, str(agents))
                print("  fixed: AGENTS.md -> %s" % AGENTS_LOCAL)
            else:
                issues.append("AGENTS.md is not a link to %s (git removed it?) — run audit --fix" % AGENTS_LOCAL)
        if localized and mirror.is_dir():  # keep the mirror current from healthy (untracked, ignored) local docs
            for r in mine + [str(f.relative_to(p)) for d in ("docs/ref", ".claude/skills") for f in (p / d).rglob("*")
                             if (p / d).is_dir() and f.is_file()]:
                cur = p / r
                if cur.is_file() and not cur.is_symlink() and r not in tracked and is_ignored(p, r) \
                        and r not in ("CLAUDE.md", "AGENTS.md") and not tracked_at(p, "HEAD", r):
                    mirror_put(mirror, r, cur)  # an older different copy moves to .history/, never lost
    print("%s: v2 — type %s — %s" % (slug, ptype, "OK" if not issues else "%d issue(s)" % len(issues)))
    for i in issues:
        print("  - " + i)
    return EXIT_OK if not issues else EXIT_FAIL


def cmd_status(args, run_dir):
    for pr in sorted(run_dir.iterdir()) if run_dir.is_dir() else []:
        plan_f = pr / "plan.json"
        if not pr.is_dir() or ".old-" in pr.name:
            continue
        if not plan_f.exists():
            if (pr / "manual.txt").exists():
                print("%-60s %s" % (pr.name, (pr / "manual.txt").read_text().strip()))
            continue
        plan = json.loads(plan_f.read_text(encoding="utf-8"))
        stage = "prepared"
        for f, s in (("verify.json", "verified"), ("commit.json", "committed"), ("applied.json", "applied"),
                     ("adopt.json", "adopted"), ("localized.json", "localized")):
            if (pr / f).exists():
                stage = s
        v = json.loads((pr / "verify.json").read_text()) if (pr / "verify.json").exists() else {"fails": [], "warns": []}
        print("%-45s %-8s %-9s fail=%d warn=%d %s" % (plan["slug"], plan["mode"], stage, len(v["fails"]),
                                                     len(v["warns"]), (v["fails"] or [""])[0][:80]))
    return EXIT_OK


def main(argv=None):
    ap = argparse.ArgumentParser(prog="docsmig", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, default=None, help="run dir (default $DOCSMIG_RUN or _backups/docs-migration-<date>)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("activity"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("preflight"); s.add_argument("--fetch", action="store_true"); s.add_argument("slugs", nargs="*")
    s = sub.add_parser("prepare"); s.add_argument("slug"); s.add_argument("--force", action="store_true")
    s.add_argument("--mode", choices=["git", "in-place"], default=None,
                   help="user-approved override of a manual blocker that local-only docs make moot")
    s.add_argument("--base", default=None, help="git mode: build the docs commit on this ref (e.g. origin/main) instead of HEAD")
    for name in ("verify", "commit", "apply"):
        s = sub.add_parser(name); s.add_argument("slug")
    s = sub.add_parser("audit"); s.add_argument("slug")
    s.add_argument("--fix", action="store_true",
                   help="localized repos: restore missing local docs from the mirror, re-create the AGENTS.md link")
    s = sub.add_parser("localize"); s.add_argument("slug")
    s.add_argument("--check", action="store_true", help="run every precondition, change nothing")
    s.add_argument("--link-from", default=None, metavar="DIR", help="link the docs to a shared folder (worktrees)")
    s.add_argument("--ack-upstream-docs", action="store_true",
                   help="proceed although upstream commits changed the old docs (port those edits afterwards)")
    s.add_argument("--deploy-reviewed", action="append", metavar="REL",
                   help="deploy script checked by hand: it never uploads the project root's docs")
    s.add_argument("--ack-legacy-loss", action="store_true",
                   help="--link-from: drop this worktree's legacy lines the shared docs lack (they stay in git history)")
    s = sub.add_parser("materialize"); s.add_argument("slug"); s.add_argument("dir")
    s = sub.add_parser("adopt"); s.add_argument("slug"); s.add_argument("--strategy", choices=["ff", "pull"], default=None)
    s = sub.add_parser("restore"); s.add_argument("slug"); s.add_argument("--after-adopt", action="store_true")
    s.add_argument("--after-localize", action="store_true")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    run_dir = (args.run or default_run()).expanduser()
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(run_dir, 0o700)
    except OSError:
        pass
    fn = {"activity": cmd_activity, "preflight": cmd_preflight, "prepare": cmd_prepare, "verify": cmd_verify,
          "commit": cmd_commit, "localize": cmd_localize, "materialize": cmd_materialize, "apply": cmd_apply, "adopt": cmd_adopt, "restore": cmd_restore,
          "audit": cmd_audit, "status": cmd_status}[args.cmd]
    try:
        return fn(args, run_dir)
    except DocsmigError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return e.code
    except subprocess.TimeoutExpired as e:
        print("ERROR: timeout: %s" % e, file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
