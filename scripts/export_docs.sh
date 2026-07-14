#!/usr/bin/env bash
set -euo pipefail

FORMAT="${1:-docx}"

case "$FORMAT" in
  docx|html|pdf)
    ;;
  *)
    echo "Usage: scripts/export_docs.sh [docx|html|pdf]" >&2
    exit 2
    ;;
esac

if [ -x scripts/render_charts.sh ]; then
  scripts/render_charts.sh
fi

if command -v pandoc >/dev/null 2>&1; then
  pandoc docs/lastenheft.md -o "docs/lastenheft.${FORMAT}"
  pandoc docs/pflichtenheft.md -o "docs/pflichtenheft.${FORMAT}"
elif command -v docker >/dev/null 2>&1; then
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/data" pandoc/core \
    docs/lastenheft.md -o "docs/lastenheft.${FORMAT}"
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/data" pandoc/core \
    docs/pflichtenheft.md -o "docs/pflichtenheft.${FORMAT}"
else
  echo "Neither pandoc nor docker is available. See docs/toolstack.md." >&2
  exit 1
fi

echo "Generated docs/lastenheft.${FORMAT}"
echo "Generated docs/pflichtenheft.${FORMAT}"
