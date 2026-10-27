#!/usr/bin/env bash
# make-slides — wraps `slidev export` to produce PDF + PPTX + HTML from a markdown deck.
#
# Usage:
#   render.sh <input.md> [output_stem] [--format all|pdf|pptx|html] [--theme org|client]
#
# Requires:
#   npm install -g @slidev/cli
#   Node 18+

set -euo pipefail

INPUT="${1:-}"
[ -z "$INPUT" ] && { echo "Usage: render.sh <input.md> [output_stem] [--format all|pdf|pptx|html]" >&2; exit 1; }
[ ! -f "$INPUT" ] && { echo "ERROR: input not found: $INPUT" >&2; exit 1; }

# Compute output stem
INPUT_ABS="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
OUTPUT_STEM="${2:-${INPUT_ABS%.*}}"
case "${2:-}" in
  --*) OUTPUT_STEM="${INPUT_ABS%.*}" ;;
esac

# Parse flags
FORMAT="all"
THEME="org"
shift || true
shift 2>/dev/null || true
while [ $# -gt 0 ]; do
  case "$1" in
    --format) FORMAT="$2"; shift 2 ;;
    --theme) THEME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Pre-flight
command -v slidev >/dev/null 2>&1 || {
  echo "ERROR: Slidev not installed. Run: npm install -g @slidev/cli" >&2
  exit 1
}

OUTPUT_DIR="$(dirname "$OUTPUT_STEM")"
STEM_NAME="$(basename "$OUTPUT_STEM")"
mkdir -p "$OUTPUT_DIR"

# Auto-insert slide separators if missing (split at every H1)
WORK_MD="$OUTPUT_DIR/.${STEM_NAME}.slidev.md"
if ! grep -q "^---$" "$INPUT"; then
  echo "    auto-inserting slide separators at H1 boundaries"
  awk '
    BEGIN { first=1 }
    /^# / {
      if (!first) print "\n---\n";
      first=0;
      print; next
    }
    { print }
  ' "$INPUT" > "$WORK_MD"
else
  cp "$INPUT" "$WORK_MD"
fi

# Inject frontmatter if missing
if ! head -1 "$WORK_MD" | grep -q "^---$"; then
  TITLE=$(grep -m1 "^# " "$WORK_MD" | sed 's/^# //' | head -c 80)
  FM="---\ntheme: seriph\ntitle: $TITLE\nfonts:\n  sans: 'Host Grotesk'\n  serif: 'Space Grotesk'\n  mono: 'JetBrains Mono'\nlineNumbers: false\nhighlighter: shiki\n---\n\n"
  TMP=$(mktemp)
  printf "$FM" > "$TMP"
  cat "$WORK_MD" >> "$TMP"
  mv "$TMP" "$WORK_MD"
fi

cd "$OUTPUT_DIR"

case "$FORMAT" in
  pdf|all)
    echo "==> rendering PDF -> $OUTPUT_STEM.pdf"
    slidev export "$WORK_MD" --output "$OUTPUT_STEM.pdf" --format pdf --timeout 60000 --with-clicks 2>&1 | tail -5 || echo "WARN: PDF export failed"
    ;;
esac

case "$FORMAT" in
  pptx|all)
    echo "==> rendering PPTX -> $OUTPUT_STEM.pptx"
    slidev export "$WORK_MD" --output "$OUTPUT_STEM.pptx" --format pptx --timeout 60000 --with-clicks 2>&1 | tail -5 || echo "WARN: PPTX export failed"
    ;;
esac

case "$FORMAT" in
  html|all)
    echo "==> rendering HTML -> $OUTPUT_STEM-html/"
    slidev build "$WORK_MD" --out "$OUTPUT_STEM-html" --base "./" 2>&1 | tail -5 || echo "WARN: HTML build failed"
    ;;
esac

# Clean up working file
rm -f "$WORK_MD"

echo
echo "==> done"
[ -f "$OUTPUT_STEM.pdf" ] && echo "    PDF:  $OUTPUT_STEM.pdf  ($(du -h "$OUTPUT_STEM.pdf" | cut -f1))"
[ -f "$OUTPUT_STEM.pptx" ] && echo "    PPTX: $OUTPUT_STEM.pptx ($(du -h "$OUTPUT_STEM.pptx" | cut -f1))"
[ -d "$OUTPUT_STEM-html" ] && echo "    HTML: $OUTPUT_STEM-html/index.html"
