#!/usr/bin/env bash
# Mirror the generic skills from the private source of truth, scrubbed and leak-gated.
#
# The private workspace is authoritative for the AUTO list below (fully generic skills with
# no client/people/infra references). For each, this copies it, runs the scrub
# (brand -> neutral, paths -> placeholders, memory links stripped), then runs the leak gate.
# If ANY auto skill fails the gate the whole sync ABORTS and nothing is written.
#
# The PUBLIC_MAINTAINED list is NOT synced: those skills carry client/infra detail in the
# private source that cannot be auto-scrubbed, so their public copies are hand-cleaned and
# edited directly in THIS repo. Sync never touches them.
#
#   scripts/sync-from-private.sh [path-to-private-repo]
#   or set PRIVATE_SKILLS_REPO; default: ../skills-private
#
# Optional: AGENT_SKILLS_BLOCKLIST -> newline-separated client/people proper nouns to also
# gate on (kept out of this public repo). Defaults to <private-repo>/.blocklist when present.
#
# After it runs clean: review `git diff`, then branch + PR.
set -euo pipefail
export PATH=/usr/bin:/bin:/usr/sbin:/sbin

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PRIV="${1:-${PRIVATE_SKILLS_REPO:-$ROOT/../skills-private}}"
SRC="$PRIV/skills"
[ -d "$SRC" ] || { echo "private skills dir not found: $SRC" >&2; exit 1; }
[ -z "${AGENT_SKILLS_BLOCKLIST:-}" ] && [ -f "$PRIV/.blocklist" ] && export AGENT_SKILLS_BLOCKLIST="$PRIV/.blocklist"
[ -z "${AGENT_SKILLS_WORKSPACE:-}" ] && export AGENT_SKILLS_WORKSPACE="$(basename "$(dirname "$PRIV")")"

# Fully-generic skills — safe to regenerate straight from private each sync.
AUTO="backend-architecture build-review-loop capability-intake competitor-market-analysis \
context-audit data-analysis-insights data-privacy-security frontend-system-design idea-validator \
intellectual-property-licensing international-legal-research legal-document-drafter llm-council \
password-authentication-security privacy-data-protection-law project-estimation-planning \
project-start rea-research requirements-business-analyst secrets-credential-manager seo-tech-stack \
shopify-ui-audit sop-process-builder task-dispatch tech-research-intelligence technical-feasibility \
update-md"

# Hand-cleaned in this repo; never synced (edit directly, re-gate manually):
#   dev-agents dev-patterns make-slides setup-project-context site-incident

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/skills"
n=0
for s in $AUTO; do
  if [ -d "$SRC/$s" ]; then cp -R "$SRC/$s" "$TMP/skills/"; n=$((n+1)); else echo "WARN missing in private: $s" >&2; fi
done
echo "copied $n auto skills from private"

python3 "$ROOT/scripts/scrub_gate.py" scrub "$TMP"       # scrub + gate; nonzero aborts (set -e)

# Gate passed — replace only the auto skills, leave hand-maintained ones intact.
for s in $AUTO; do
  [ -d "$TMP/skills/$s" ] || continue
  rm -rf "$ROOT/skills/$s"
  cp -R "$TMP/skills/$s" "$ROOT/skills/"
done

# Final belt-and-braces: gate the whole repo (incl. hand-maintained skills).
python3 "$ROOT/scripts/scrub_gate.py" gate "$ROOT"
python3 "$ROOT/scripts/build-readme.py"
echo "sync OK: $n auto skills refreshed, README rebuilt. Review git diff, then PR."
