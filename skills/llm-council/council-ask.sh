#!/usr/bin/env bash
# council-ask.sh — route an arbitrary prompt to a reachable EXTERNAL LLM, or detect which are reachable.
#
# Part of the llm-council skill. Lets the council seat REAL external models as advisors when they're
# live, so the council gets genuine cross-model diversity (the thing that makes peer review worth more
# than "ask one model five times"). When nothing external is reachable, the skill falls back to Claude
# sub-agent lenses — this script just reports "nothing reachable" and the skill degrades honestly.
#
# Usage:
#   council-ask.sh --detect                       # print reachable providers, one per line; exit 0
#   council-ask.sh <provider> [--model ID] [--system TEXT] [--max N]   # prompt on stdin -> reply on stdout
#     provider: kimi | deepseek | openrouter | codex
#
# Reuses the same key files as panel-review.sh:
#   kimi       -> $MOONSHOT_API_KEY   or ~/.config/moonshot/key
#   deepseek   -> $DEEPSEEK_API_KEY   or ~/.config/deepseek/key
#   openrouter -> $OPENROUTER_API_KEY or ~/.config/openrouter/key
#   codex      -> the `codex` CLI on PATH (uses `codex exec`)
#
# Exit codes: 0 ok · 2 usage · 3 no key/CLI · 4 network · 5 http!=200 · 7 parse
set -uo pipefail

API_PROVIDERS="kimi deepseek openrouter"

resolve_key() {
  case "$1" in
    kimi)       [ -n "${MOONSHOT_API_KEY:-}" ]   && { printf '%s' "$MOONSHOT_API_KEY";   return; }; [ -f "$HOME/.config/moonshot/key" ]   && tr -d ' \t\r\n' < "$HOME/.config/moonshot/key" ;;
    deepseek)   [ -n "${DEEPSEEK_API_KEY:-}" ]   && { printf '%s' "$DEEPSEEK_API_KEY";   return; }; [ -f "$HOME/.config/deepseek/key" ]   && tr -d ' \t\r\n' < "$HOME/.config/deepseek/key" ;;
    openrouter) [ -n "${OPENROUTER_API_KEY:-}" ] && { printf '%s' "$OPENROUTER_API_KEY"; return; }; [ -f "$HOME/.config/openrouter/key" ] && tr -d ' \t\r\n' < "$HOME/.config/openrouter/key" ;;
  esac
}

meta() { # -> "URL DEFAULT_MODEL"
  case "$1" in
    kimi)       echo "https://api.moonshot.ai/v1/chat/completions kimi-k2-0905-preview" ;;
    deepseek)   echo "https://api.deepseek.com/chat/completions deepseek-chat" ;;
    openrouter) echo "https://openrouter.ai/api/v1/chat/completions openai/gpt-4o-mini" ;;
  esac
}

# OpenAI-compatible chat program. Config via env; PROMPT via stdin — unbounded, no argv/env size limit.
# All string literals use double quotes so the whole program can live in a single-quoted shell var.
PYPROG='
import os, sys, json, urllib.request, urllib.error
url=os.environ["CA_URL"]; key=os.environ["CA_KEY"]; model=os.environ["CA_MODEL"]
system=os.environ.get("CA_SYSTEM",""); maxtok=int(os.environ.get("CA_MAXTOK","1024"))
prompt=sys.stdin.read()
msgs=[{"role":"system","content":system}] if system else []
msgs.append({"role":"user","content":prompt})
body=json.dumps({"model":model,"messages":msgs,"max_tokens":maxtok,"temperature":0.7}).encode()
req=urllib.request.Request(url,data=body,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
try:
    with urllib.request.urlopen(req,timeout=90) as r:
        data=json.load(r)
except urllib.error.HTTPError as e:
    sys.stderr.write("http %d: %s\n"%(e.code, e.read().decode("utf-8","replace")[:200])); sys.exit(5)
except Exception as e:
    sys.stderr.write("network: %s\n"%e); sys.exit(4)
try:
    sys.stdout.write(data["choices"][0]["message"]["content"])
except Exception:
    sys.stderr.write("parse: unexpected response shape\n"); sys.exit(7)
'
call_openai() { # args: url key model system maxtok prompt  -> reply on stdout
  printf '%s' "$6" | CA_URL="$1" CA_KEY="$2" CA_MODEL="$3" CA_SYSTEM="$4" CA_MAXTOK="$5" python3 -c "$PYPROG"
}

ping_api() { # $1 provider -> 0 if a 1-token request returns 200
  local key url model
  key="$(resolve_key "$1")"; [ -z "$key" ] && return 1
  read -r url model <<<"$(meta "$1")"
  call_openai "$url" "$key" "$model" "" "1" "hi" >/dev/null 2>&1
}

# ---- --detect ----
if [ "${1:-}" = "--detect" ]; then
  for p in $API_PROVIDERS; do ping_api "$p" && echo "$p"; done
  # codex counts only if the CLI is present AND logged in — an installed-but-unauthed CLI would fail every call.
  command -v codex >/dev/null 2>&1 && codex login status 2>&1 | grep -qi "logged in" && echo "codex"
  exit 0
fi

# ---- prompt a specific provider ----
PROVIDER="${1:-}"; shift 2>/dev/null || true
[ -z "$PROVIDER" ] && { echo "usage: council-ask.sh --detect | <provider> [--model ID] [--system TEXT] [--max N]" >&2; exit 2; }

MODEL_OVERRIDE=""; SYSTEM=""; MAXTOK="1024"
while [ $# -gt 0 ]; do
  case "$1" in
    --model)  MODEL_OVERRIDE="${2:-}"; shift 2 || shift ;;
    --system) SYSTEM="${2:-}"; shift 2 || shift ;;
    --max)    MAXTOK="${2:-1024}"; shift 2 || shift ;;
    *) echo "council-ask: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

if [ "$PROVIDER" = "codex" ]; then
  command -v codex >/dev/null 2>&1 || { echo "council-ask: codex CLI not installed" >&2; exit 3; }
  PROMPT="$(cat)"
  [ -n "$SYSTEM" ] && PROMPT="$SYSTEM"$'\n\n'"$PROMPT"
  OUT="$(mktemp)"
  # read-only sandbox: an advisor answers a question, it must not touch the workspace.
  # prompt via stdin (`-`), not argv — avoids E2BIG on large prompts and any leading-dash flag parsing.
  if printf '%s' "$PROMPT" | codex exec --skip-git-repo-check --sandbox read-only -o "$OUT" - >/dev/null 2>&1; then
    cat "$OUT"; rm -f "$OUT"; exit 0
  fi
  rm -f "$OUT"; echo "council-ask: codex exec failed" >&2; exit 4
fi

case " $API_PROVIDERS " in
  *" $PROVIDER "*) ;;
  *) echo "council-ask: unknown provider '$PROVIDER' (kimi|deepseek|openrouter|codex)" >&2; exit 2 ;;
esac

KEY="$(resolve_key "$PROVIDER")"
[ -z "$KEY" ] && { echo "council-ask: no API key for '$PROVIDER'" >&2; exit 3; }
read -r URL DEFMODEL <<<"$(meta "$PROVIDER")"
MODEL="${MODEL_OVERRIDE:-$DEFMODEL}"
PROMPT="$(cat)"
call_openai "$URL" "$KEY" "$MODEL" "$SYSTEM" "$MAXTOK" "$PROMPT"
