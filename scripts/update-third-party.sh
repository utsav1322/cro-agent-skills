#!/usr/bin/env bash
# Pull every third-party skill and plugin we take from somewhere to its latest version,
# update the local ~/.claude install, and write the resolved version/commit back into
# third-party-sources.json. Review `git diff`, then open a PR.
#
#   scripts/update-third-party.sh            update everything
#   scripts/update-third-party.sh --check    report latest vs synced, change nothing
#
# Needs: gh (authenticated), npx, python3, and the VS Code-bundled `claude` for plugins.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.npm-global/bin:$HOME/.local/bin
export DISABLE_TELEMETRY=1 DO_NOT_TRACK=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/third-party-sources.json"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
CLAUDE_BIN="$(ls -t "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | head -1 || true)"
command -v claude >/dev/null 2>&1 && CLAUDE_BIN="${CLAUDE_BIN:-claude}"

latest() { gh api "repos/$1/commits/HEAD" --jq '.sha[0:7]+" "+.commit.committer.date[0:10]'; }

echo "== npx skills sources"
python3 - "$MANIFEST" <<'PY' | while IFS=$'\t' read -r repo skills synced; do
import json,sys
d=json.load(open(sys.argv[1]))
for e in d["npx_skills"]:
    print(e["repo"]+"\t"+",".join(e["skills"])+"\t"+e.get("synced_commit",""))
PY
  read -r cur date <<<"$(latest "$repo")"
  if [ "$cur" = "$synced" ]; then
    echo "  $repo  up to date ($cur)"
  else
    echo "  $repo  $synced -> $cur ($date)"
    if [ "$CHECK" = 0 ]; then
      # shellcheck disable=SC2086
      npx -y skills@1.7.4 add "$repo" -g -a claude-code --copy -y -s ${skills//,/ } >/dev/null 2>&1 \
        && echo "    reinstalled" || echo "    REINSTALL FAILED — check manually"
      python3 - "$MANIFEST" "$repo" "$cur" "$date" <<'PY'
import json,sys
p,repo,sha,date=sys.argv[1:5]
d=json.load(open(p))
for e in d["npx_skills"]:
    if e["repo"]==repo: e["synced_commit"]=sha; e["synced_date"]=date
json.dump(d,open(p,"w"),indent=2); open(p,"a").write("\n")
PY
    fi
  fi
done

echo "== plugins"
if [ -n "$CLAUDE_BIN" ]; then
  python3 -c 'import json,sys;[print(p["name"]) for p in json.load(open(sys.argv[1]))["plugins"]]' "$MANIFEST" | while read -r name; do
    if [ "$CHECK" = 0 ]; then
      "$CLAUDE_BIN" plugin update "$name" --scope user 2>&1 | tail -1 | sed "s/^/  $name: /"
    else
      echo "  $name (run without --check to update)"
    fi
  done
  # record installed plugin versions
  if [ "$CHECK" = 0 ]; then
    "$CLAUDE_BIN" plugin list 2>/dev/null | awk '/@/{n=$2} /Version:/{print n"\t"$2}' > /tmp/_plugver.$$
    python3 - "$MANIFEST" /tmp/_plugver.$$ <<'PY'
import json,sys
p,vf=sys.argv[1:3]
ver=dict(l.strip().split("\t") for l in open(vf) if "\t" in l)
d=json.load(open(p))
for e in d["plugins"]:
    if e["name"] in ver: e["version"]=ver[e["name"]]
json.dump(d,open(p,"w"),indent=2); open(p,"a").write("\n")
PY
    rm -f /tmp/_plugver.$$
  fi
else
  echo "  claude binary not found — update plugins manually with: claude plugin update <name> --scope user"
fi

echo "== manual-pinned (hand-curated subsets; report only, re-pull by hand)"
python3 -c 'import json,sys;[print(e["repo"]+"\t"+e.get("pinned_sha","")) for e in json.load(open(sys.argv[1])).get("manual_pinned",[])]' "$MANIFEST" | while IFS=$'\t' read -r repo pinned; do
  read -r cur date <<<"$(latest "$repo")"
  short_pin="${pinned:0:7}"
  if [ "$cur" = "$short_pin" ]; then
    echo "  $repo  pinned $short_pin — up to date"
  else
    echo "  $repo  pinned $short_pin -> upstream $cur ($date). REVIEW upstream changes, then hand-copy the wanted skills and bump pinned_sha. Not auto-pulled."
  fi
done

echo "== gstack (self-updating): run the gstack-upgrade skill or 'npx gstack@latest' separately"
[ "$CHECK" = 0 ] && python3 "$ROOT/scripts/build-readme.py" || true
echo "Done. Review 'git diff', then branch + PR."
